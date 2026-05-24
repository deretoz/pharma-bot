# rl_bridge.py
# Puente entre el agente RL entrenado y el bot en tiempo real

import os
import numpy as np
from stable_baselines3 import PPO

MODEL_PATH = 'models/pharma_ppo'

# ── Cargar modelo ────────────────────────────────────
def load_model():
    if not os.path.exists(f'{MODEL_PATH}.zip'):
        print('[RL] Modelo no encontrado — usando solo swarm')
        return None
    try:
        model = PPO.load(MODEL_PATH)
        print('[RL] Modelo cargado correctamente')
        return model
    except Exception as e:
        print(f'[RL ERROR] {e}')
        return None

# Carga el modelo una sola vez al importar
_model = load_model()

# ── Construir observación desde oportunidad ──────────
def build_observation(opp, signal):
    price = opp.get('price_data') or {}
    obs   = np.array([
        float(price.get('current',      50)) / 100,  # precio normalizado
        float(price.get('change_30d',    0)) / 100,  # cambio 30d
        float(price.get('volume_ratio',  1)),          # volumen relativo
        float(signal.get('p_success',  0.5)),          # prob swarm
        float(signal.get('p_failure',  0.3)),          # prob fallo
        float(signal.get('p_neutral',  0.2)),          # prob neutral
        0.0,                                           # posición actual
        0.0                                            # pnl actual
    ], dtype=np.float32)
    return obs

# ── Obtener acción del agente RL ─────────────────────
def get_rl_action(opp, signal):
    if _model is None:
        return None

    try:
        obs        = build_observation(opp, signal)
        action, _  = _model.predict(obs, deterministic=True)
        action_map = {0: 'MANTENER', 1: 'COMPRAR', 2: 'VENDER'}
        return action_map[int(action)]
    except Exception as e:
        print(f'[RL ERROR] {e}')
        return None

# ── Combinar swarm + RL ──────────────────────────────
def get_combined_signal(opp, signal):
    """
    Combina la señal del swarm con la del agente RL.
    Solo actúa cuando AMBOS están de acuerdo.
    """
    rl_action = get_rl_action(opp, signal)

    if rl_action is None:
        # Sin modelo RL — usar solo swarm
        return signal

    swarm_action = signal['accion']

    print(f'    Swarm: {swarm_action} | RL: {rl_action}')

    # Ambos de acuerdo → alta confianza
    if rl_action == swarm_action:
        signal['accion']      = swarm_action
        signal['edge']        = min(signal['edge'] * 1.25, 0.30)
        signal['rl_accion']   = rl_action
        signal['rl_acuerdo']  = True
        print(f'    ✅ Consenso RL+Swarm: {swarm_action} — edge aumentado')

    # Desacuerdo → MANTENER por precaución
    else:
        signal['accion']     = 'MANTENER'
        signal['edge']       = signal['edge'] * 0.50
        signal['rl_accion']  = rl_action
        signal['rl_acuerdo'] = False
        print(f'    ⚠️  Desacuerdo RL+Swarm → MANTENER')

    return signal

# ── Test ─────────────────────────────────────────────
if __name__ == '__main__':
    print('=== Test RL Bridge ===')

    test_opp = {
        'ticker':  'ARWR',
        'company': 'Arrowhead Pharmaceuticals',
        'reasons': ['7 ensayo(s) Fase III'],
        'trials':  [{'phase': 'PHASE3'}] * 7,
        'price_data': {
            'current':      75.50,
            'change_30d':   -3.2,
            'volume_ratio': 1.4
        }
    }

    test_signal = {
        'accion':      'COMPRAR',
        'p_success':   0.662,
        'p_failure':   0.186,
        'p_neutral':   0.151,
        'edge':        0.162,
        'probabilidad':66.2,
        'votos':       '4/5'
    }

    result = get_combined_signal(test_opp, test_signal)

    print(f'\nSeñal final:')
    print(f'  Acción:     {result["accion"]}')
    print(f'  Edge:       {result["edge"]}')
    print(f'  RL acuerdo: {result.get("rl_acuerdo")}')
    print('=== OK ===')