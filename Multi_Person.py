# Multi_Person.py — Swarm v2
# Agentes con output de distribución de probabilidad matemática estricta

import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# ── Prompts de los 5 agentes ─────────────────────────
PERSONAS = {
    'biotech_analyst': """Eres un analista cuantitativo de biotecnología con 15 años de experiencia 
evaluando ensayos clínicos para fondos de inversión institucionales.
Tu única función es convertir datos científicos de ensayos clínicos en probabilidades matemáticas.

Reglas estrictas:
1. Evalúa la fase clínica y cantidad de ensayos activos.
2. Basa tus estimaciones en tasas históricas de éxito por fase:
   - Fase II activa: base p_success 0.28
   - Fase III activa: base p_success 0.58
   - Múltiples ensayos Fase III: aumenta p_success hasta 0.72
3. p_success + p_failure + p_neutral debe sumar exactamente 1.0.
4. Cero texto fuera del JSON.

Responde ÚNICAMENTE con este JSON exacto:
{"p_success": 0.0, "p_failure": 0.0, "p_neutral": 0.0, "confidence": 0.0, "time_horizon_days": 30, "risk_factors": ["factor1", "factor2"]}""",

    'fda_expert': """Eres un ex-revisor senior de la FDA con 20 años evaluando NDAs y BLAs.
Tu función es estimar la probabilidad regulatoria basándote en precedentes históricos.

Reglas estrictas:
1. Tasa base de aprobación FDA desde Fase III completa: 0.58
2. Si la empresa tiene historial FDA positivo: aumenta p_success 0.10
3. Si tiene historial de rechazos (CRL): reduce p_success 0.15
4. Sin historial conocido: usa tasa base
5. p_success + p_failure + p_neutral debe sumar exactamente 1.0.
6. Cero texto fuera del JSON.

Responde ÚNICAMENTE con este JSON exacto:
{"p_success": 0.0, "p_failure": 0.0, "p_neutral": 0.0, "confidence": 0.0, "time_horizon_days": 30, "risk_factors": ["factor1", "factor2"]}""",

    'quant_trader': """Eres un trader cuantitativo especializado en event-driven trading farmacéutico del NASDAQ.
Tu función es estimar la probabilidad de movimiento favorable del precio.

Reglas estrictas:
1. Volumen relativo > 2x: aumenta p_success 0.10
2. Precio estable 30d (cambio < 20%): aumenta p_success 0.08
3. Precio subió > 20% últimos 30d: reduce p_success 0.15 (ya priceado)
4. p_success = prob de subida > 10% en time_horizon_days
5. p_failure = prob de caída > 10%
6. p_neutral = rango entre -10% y +10%
7. p_success + p_failure + p_neutral debe sumar exactamente 1.0.
8. Cero texto fuera del JSON.

Responde ÚNICAMENTE con este JSON exacto:
{"p_success": 0.0, "p_failure": 0.0, "p_neutral": 0.0, "confidence": 0.0, "time_horizon_days": 30, "risk_factors": ["factor1", "factor2"]}""",

    'risk_manager': """Eres un gestor de riesgo institucional especializado en biotech.
Tu función es identificar vectores de riesgo que puedan hacer fallar la tesis.

Reglas estrictas:
1. Muchos ensayos simultáneos (> 5): riesgo de dilución de capital, reduce p_success 0.10
2. Precio cayendo > 15% en 30d: señal de problemas internos, reduce p_success 0.12
3. Solo Fase II sin Fase III: mayor incertidumbre, reduce p_success 0.08
4. p_success aquí = probabilidad de que la tesis NO falle
5. p_success + p_failure + p_neutral debe sumar exactamente 1.0.
6. Cero texto fuera del JSON.

Responde ÚNICAMENTE con este JSON exacto:
{"p_success": 0.0, "p_failure": 0.0, "p_neutral": 0.0, "confidence": 0.0, "time_horizon_days": 30, "risk_factors": ["factor1", "factor2"]}""",

    'contrarian': """Eres un analista contrarian especializado en detectar cuando el mercado ya priceó un catalizador.
Tu función es estimar si el movimiento favorable YA ocurrió antes del evento.

Reglas estrictas:
1. Precio subió > 15% en 30d: mercado ya lo priceó, aumenta p_failure 0.20
2. Volumen > 2x promedio antes del evento: información filtrada, aumenta p_failure 0.10
3. Precio estable o bajando: mercado no lo priceó, aumenta p_success 0.15
4. p_success = el mercado NO ha priceado el evento aún (oportunidad real)
5. p_failure = el mercado ya lo priceó (entrada tarde)
6. p_success + p_failure + p_neutral debe sumar exactamente 1.0.
7. Cero texto fuera del JSON.

Responde ÚNICAMENTE con este JSON exacto:
{"p_success": 0.0, "p_failure": 0.0, "p_neutral": 0.0, "confidence": 0.0, "time_horizon_days": 30, "risk_factors": ["factor1", "factor2"]}"""
}

# ── Consultar un agente ──────────────────────────────
def consult_agent(persona_name, persona_prompt, context):
    prompt = f"""{persona_prompt}

Contexto del análisis:
{context}

Recuerda: responde ÚNICAMENTE con el JSON. Sin texto adicional, sin markdown."""

    try:
        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=200,
            messages=[{'role': 'user', 'content': prompt}]
        )
        raw = msg.content[0].text.strip()
        raw = raw.replace('```json', '').replace('```', '').strip()
        data = json.loads(raw)

        # Validar que las probabilidades sumen 1.0
        total = data['p_success'] + data['p_failure'] + data['p_neutral']
        if abs(total - 1.0) > 0.05:
            # Normalizar si no suman exactamente 1
            data['p_success'] /= total
            data['p_failure'] /= total
            data['p_neutral'] /= total

        return data

    except Exception as e:
        print(f'  [ERROR agente {persona_name}]: {e}')
        return {
            'p_success': 0.50,
            'p_failure': 0.30,
            'p_neutral': 0.20,
            'confidence': 0.10,
            'time_horizon_days': 30,
            'risk_factors': ['error en análisis']
        }

# ── Agregador ponderado por confianza ────────────────
def aggregate_distributions(results):
    """
    Promedio ponderado por confidence.
    Agentes más seguros pesan más en la decisión final.
    """
    total_confidence = sum(r['confidence'] for r in results)
    if total_confidence == 0:
        total_confidence = 1

    p_success = sum(r['p_success'] * r['confidence'] for r in results) / total_confidence
    p_failure = sum(r['p_failure'] * r['confidence'] for r in results) / total_confidence
    p_neutral = sum(r['p_neutral'] * r['confidence'] for r in results) / total_confidence

    # Normalizar
    total = p_success + p_failure + p_neutral
    p_success /= total
    p_failure /= total
    p_neutral /= total

    # Edge sobre probabilidad base del 50%
    edge = round(p_success - 0.50, 3)

    # Acción basada en distribución
    if p_success > 0.60:
        accion = 'COMPRAR'
    elif p_failure > 0.55:
        accion = 'VENDER'
    else:
        accion = 'MANTENER'

    # Horizon promedio ponderado
    horizon = round(
        sum(r['time_horizon_days'] * r['confidence'] for r in results) / total_confidence
    )

    # Risk factors únicos de todos los agentes
    all_risks = []
    for r in results:
        all_risks.extend(r.get('risk_factors', []))
    unique_risks = list(dict.fromkeys(all_risks))[:4]

    return {
        'accion':          accion,
        'p_success':       round(p_success, 3),
        'p_failure':       round(p_failure, 3),
        'p_neutral':       round(p_neutral, 3),
        'edge':            edge,
        'probabilidad':    round(p_success * 100, 1),
        'time_horizon':    horizon,
        'risk_factors':    unique_risks,
        'votos':           f'{sum(1 for r in results if r["p_success"] > 0.5)}/5'
    }

# ── Swarm completo ───────────────────────────────────
def get_swarm_signal(opportunity):
    price = opportunity.get('price_data') or {}

    context = f"""Empresa: {opportunity['ticker']} — {opportunity['company']}
Catalizadores: {', '.join(opportunity['reasons'])}
Ensayos Fase III activos: {sum(1 for t in opportunity['trials'] if 'PHASE3' in t.get('phase',''))}
Ensayos Fase II activos: {sum(1 for t in opportunity['trials'] if 'PHASE2' in t.get('phase',''))}
Precio actual: ${price.get('current', 'N/A')}
Cambio últimos 30 días: {price.get('change_30d', 'N/A')}%
Volumen relativo: {price.get('volume_ratio', 'N/A')}x el promedio"""

    print(f'\n  Consultando swarm v2 para {opportunity["ticker"]}...')
    results = []

    for name, prompt in PERSONAS.items():
        result = consult_agent(name, prompt, context)
        results.append(result)
        print(f'    {name:20s}: p_success={result["p_success"]:.2f} | p_failure={result["p_failure"]:.2f} | conf={result["confidence"]:.2f}')

    signal = aggregate_distributions(results)

    print(f'    {"AGREGADO":20s}: accion={signal["accion"]} | edge={signal["edge"]:.3f} | p_success={signal["p_success"]:.3f}')

    return signal

# ── Test ─────────────────────────────────────────────
if __name__ == '__main__':
    print('=== Test Swarm v2 — Distribuciones de probabilidad ===')

    test_opp = {
        'ticker':     'ARWR',
        'company':    'Arrowhead Pharmaceuticals',
        'reasons':    ['7 ensayo(s) Fase III', '2 ensayo(s) Fase II', 'Precio estable 30d'],
        'trials':     [{'phase': 'PHASE3'}] * 7 + [{'phase': 'PHASE2'}] * 2,
        'price_data': {
            'current':      75.50,
            'change_30d':   -3.2,
            'volume_ratio': 1.4
        }
    }

    signal = get_swarm_signal(test_opp)

    print(f'\n  Resultado final:')
    print(f'    Acción:       {signal["accion"]}')
    print(f'    p_success:    {signal["p_success"]}')
    print(f'    p_failure:    {signal["p_failure"]}')
    print(f'    p_neutral:    {signal["p_neutral"]}')
    print(f'    Edge:         {signal["edge"]}')
    print(f'    Horizon:      {signal["time_horizon"]} días')
    print(f'    Risk factors: {signal["risk_factors"]}')
    print('=== OK ===')