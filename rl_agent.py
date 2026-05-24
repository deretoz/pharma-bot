# rl_agent.py
# Agente de Reinforcement Learning para trading farmacéutico
# Algoritmo: PPO (Proximal Policy Optimization)

import os
import numpy as np
import pandas as pd
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import EvalCallback
from rl_environment import PharmaTraidingEnv

# ── Cargar dataset ───────────────────────────────────
def load_dataset(path='data/rl_dataset.csv'):
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

# ── Dividir en train/test ────────────────────────────
def split_dataset(df, test_pct=0.2):
    tickers = df['ticker'].unique()
    train_dfs = []
    test_dfs  = []

    for ticker in tickers:
        t = df[df['ticker'] == ticker].reset_index(drop=True)
        split = int(len(t) * (1 - test_pct))
        train_dfs.append(t.iloc[:split])
        test_dfs.append(t.iloc[split:])

    train = pd.concat(train_dfs).reset_index(drop=True)
    test  = pd.concat(test_dfs).reset_index(drop=True)

    print(f'Train: {len(train)} filas | Test: {len(test)} filas')
    return train, test

# ── Entrenar agente ──────────────────────────────────
def train_agent(train_df, total_timesteps=50000):
    print(f'\nEntrenando agente PPO...')
    print(f'Dataset: {len(train_df)} pasos | Timesteps: {total_timesteps}')

    env = PharmaTraidingEnv(train_df)

    model = PPO(
        policy          = 'MlpPolicy',
        env             = env,
        learning_rate   = 3e-4,
        n_steps         = 256,
        batch_size      = 64,
        n_epochs        = 10,
        gamma           = 0.99,
        gae_lambda      = 0.95,
        clip_range      = 0.2,
        verbose         = 1
    )

    model.learn(total_timesteps=total_timesteps)

    os.makedirs('models', exist_ok=True)
    model.save('models/pharma_ppo')
    print('\nModelo guardado en models/pharma_ppo.zip')
    return model

# ── Evaluar agente en datos de test ─────────────────
def evaluate_agent(model, test_df):
    print('\nEvaluando en datos de test...')
    env   = PharmaTraidingEnv(test_df)
    obs, _= env.reset()

    done    = False
    rewards = []

    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, _ = env.step(int(action))
        rewards.append(reward)
        done = terminated or truncated

    metrics = env.get_metrics()

    print(f'\n=== Resultados en test ===')
    print(f'Total trades:   {metrics["total_trades"]}')
    print(f'Trades ganados: {metrics["winning_trades"]}')
    print(f'Win rate:       {metrics["win_rate"]}%')
    print(f'Retorno total:  {metrics["total_return"]}%')
    print(f'Capital final:  ${metrics["capital_final"]:,.2f}')
    print(f'Reward total:   {sum(rewards):.2f}')

    return metrics

# ── Comparar con baseline (buy & hold) ──────────────
def buy_and_hold_baseline(test_df):
    results = {}
    for ticker in test_df['ticker'].unique():
        t = test_df[test_df['ticker'] == ticker]
        if len(t) < 2:
            continue
        ret = (t['precio'].iloc[-1] - t['precio'].iloc[0]) / t['precio'].iloc[0] * 100
        results[ticker] = round(ret, 1)

    avg = sum(results.values()) / len(results) if results else 0
    print(f'\n=== Baseline Buy & Hold ===')
    for ticker, ret in results.items():
        print(f'  {ticker}: {ret:+.1f}%')
    print(f'  Promedio: {avg:+.1f}%')
    return avg

# ── Main ─────────────────────────────────────────────
if __name__ == '__main__':
    print('=== RL Agent — Pharma Bot ===\n')

    df = load_dataset()
    train_df, test_df = split_dataset(df)

    # Entrenar
    model = train_agent(train_df, total_timesteps=50000)

    # Evaluar
    metrics  = evaluate_agent(model, test_df)
    baseline = buy_and_hold_baseline(test_df)

    # Veredicto
    print(f'\n=== Veredicto ===')
    if metrics['total_return'] > baseline:
        diff = metrics['total_return'] - baseline
        print(f'✅ El agente RL supera Buy&Hold por {diff:.1f}%')
    else:
        diff = baseline - metrics['total_return']
        print(f'⚠️  Buy&Hold supera al agente por {diff:.1f}% — seguir entrenando')

    print('\n=== FIN ===')