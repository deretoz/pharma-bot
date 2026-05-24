# rl_environment.py
# Entorno de trading farmacéutico para Reinforcement Learning

import numpy as np
import gymnasium as gym
from gymnasium import spaces

class PharmaTraidingEnv(gym.Env):
    """
    Entorno de trading farmacéutico para RL.
    
    State Space (lo que el agente observa):
    - precio_normalizado
    - cambio_30d
    - volumen_ratio
    - p_success (del swarm)
    - p_failure (del swarm)
    - p_neutral (del swarm)
    - posicion_actual (-1=short, 0=flat, 1=long)
    - pnl_actual (ganancia/pérdida de posición abierta)
    
    Action Space (lo que el agente puede hacer):
    - 0 = MANTENER
    - 1 = COMPRAR
    - 2 = VENDER
    """

    metadata = {'render_modes': ['human']}

    def __init__(self, df, initial_capital=100000,
                 max_position_pct=0.05, stop_loss_pct=0.15):
        super().__init__()

        self.df              = df.reset_index(drop=True)
        self.initial_capital = initial_capital
        self.max_pos_pct     = max_position_pct
        self.stop_loss_pct   = stop_loss_pct

        # Action Space: 0=MANTENER, 1=COMPRAR, 2=VENDER
        self.action_space = spaces.Discrete(3)

        # State Space: 8 variables continuas
        self.observation_space = spaces.Box(
            low  = np.array([-5, -1, 0, 0, 0, 0, -1, -1], dtype=np.float32),
            high = np.array([ 5,  1, 10, 1, 1, 1,  1,  1], dtype=np.float32),
            dtype= np.float32
        )

        self.reset()

    def _get_obs(self):
        row = self.df.iloc[self.current_step]
        return np.array([
            float(row.get('precio_norm',    0)),
            float(row.get('change_30d',     0)) / 100,
            float(row.get('volume_ratio',   1)),
            float(row.get('p_success',    0.5)),
            float(row.get('p_failure',    0.3)),
            float(row.get('p_neutral',    0.2)),
            float(self.position),
            float(self.unrealized_pnl)
        ], dtype=np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step    = 0
        self.capital         = self.initial_capital
        self.position        = 0      # -1, 0, 1
        self.entry_price     = 0
        self.unrealized_pnl  = 0
        self.total_trades    = 0
        self.winning_trades  = 0
        self.portfolio_value = self.initial_capital
        self.history         = []
        return self._get_obs(), {}

    def step(self, action):
        row           = self.df.iloc[self.current_step]
        current_price = float(row.get('precio', 1))
        position_size = self.capital * self.max_pos_pct

        reward = 0

        # ── Ejecutar acción ──────────────────────────
        if action == 1 and self.position == 0:  # COMPRAR
            self.position    = 1
            self.entry_price = current_price
            self.total_trades += 1

        elif action == 2 and self.position == 1:  # VENDER
            pnl_pct = (current_price - self.entry_price) / self.entry_price
            pnl_usd = position_size * pnl_pct
            self.capital    += pnl_usd
            reward           = pnl_pct * 100  # reward = % ganancia
            if pnl_pct > 0:
                self.winning_trades += 1
            self.position        = 0
            self.entry_price     = 0
            self.unrealized_pnl  = 0

        # ── Stop loss automático ─────────────────────
        if self.position == 1 and self.entry_price > 0:
            self.unrealized_pnl = (
                (current_price - self.entry_price) / self.entry_price
            )
            if self.unrealized_pnl <= -self.stop_loss_pct:
                pnl_usd = position_size * self.unrealized_pnl
                self.capital        += pnl_usd
                reward               = self.unrealized_pnl * 100
                self.position        = 0
                self.entry_price     = 0
                self.unrealized_pnl  = 0

        # ── Penalización por inactividad excesiva ────
        if action == 0 and self.position == 0:
            reward -= 0.01  # pequeña penalización por no hacer nada

        # ── Avanzar al siguiente paso ────────────────
        self.current_step    += 1
        self.portfolio_value  = self.capital

        terminated = self.current_step >= len(self.df) - 1
        truncated  = self.capital < self.initial_capital * 0.5  # ruina

        self.history.append({
            'step':            self.current_step,
            'precio':          current_price,
            'action':          action,
            'reward':          reward,
            'portfolio_value': self.portfolio_value
        })

        return self._get_obs(), reward, terminated, truncated, {}

    def get_metrics(self):
        win_rate = (
            self.winning_trades / self.total_trades * 100
            if self.total_trades > 0 else 0
        )
        total_return = (
            (self.portfolio_value - self.initial_capital)
            / self.initial_capital * 100
        )
        return {
            'total_trades':  self.total_trades,
            'winning_trades':self.winning_trades,
            'win_rate':      round(win_rate, 1),
            'total_return':  round(total_return, 1),
            'capital_final': round(self.portfolio_value, 2)
        }

    def render(self):
        print(f'Step {self.current_step} | '
              f'Capital: ${self.portfolio_value:,.2f} | '
              f'Posición: {self.position} | '
              f'PnL: {self.unrealized_pnl:.2%}')


# ── Test del entorno ─────────────────────────────────
if __name__ == '__main__':
    import pandas as pd

    print('=== Test PharmaTraidingEnv ===')

    # Dataset de prueba simulado
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        'precio':       np.random.uniform(50, 100, n),
        'precio_norm':  np.random.uniform(-1, 1, n),
        'change_30d':   np.random.uniform(-20, 20, n),
        'volume_ratio': np.random.uniform(0.5, 3, n),
        'p_success':    np.random.uniform(0.4, 0.8, n),
        'p_failure':    np.random.uniform(0.1, 0.4, n),
        'p_neutral':    np.random.uniform(0.1, 0.3, n),
    })

    env = PharmaTraidingEnv(df)
    obs, _ = env.reset()

    print(f'Observation space: {env.observation_space.shape}')
    print(f'Action space: {env.action_space.n}')
    print(f'Observación inicial: {obs}')

    # Simular 20 pasos con acciones aleatorias
    for i in range(20):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, _ = env.step(action)
        if terminated or truncated:
            break

    metrics = env.get_metrics()
    print(f'\nMétricas tras 20 pasos aleatorios:')
    print(f'  Trades: {metrics["total_trades"]}')
    print(f'  Win rate: {metrics["win_rate"]}%')
    print(f'  Retorno: {metrics["total_return"]}%')
    print(f'  Capital final: ${metrics["capital_final"]:,.2f}')
    print('=== OK ===')