# multi_persona.py
import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# ── Las 5 personalidades ─────────────────────────────
PERSONAS = {
    'biotech_analyst': '''Eres analista de biotecnología con 15 años de experiencia 
en ensayos clínicos. Evalúa la solidez científica del catalizador y la probabilidad 
de éxito del ensayo basándote en la fase, cantidad de ensayos activos y estabilidad 
del precio. Sé directo y conciso.''',

    'fda_expert': '''Eres ex-revisor senior de la FDA con 20 años de experiencia. 
Evalúa la probabilidad de aprobación regulatoria basándote en el historial de la 
empresa, la fase de los ensayos activos y precedentes similares en el sector. 
Sé directo y conciso.''',

    'quant_trader': '''Eres trader cuantitativo especializado en acciones farmacéuticas 
del NASDAQ. Analiza el momentum del precio, el volumen relativo y la relación 
riesgo/recompensa de entrar ahora. Sé directo y conciso.''',

    'risk_manager': '''Eres gestor de riesgo conservador especializado en biotech. 
Identifica las principales razones por las que esta inversión podría fallar: 
dilución de capital, competidores, datos negativos, o sobrevaluación. 
Sé directo y conciso.''',

    'contrarian': '''Eres el escéptico del equipo de inversión. Tu trabajo es asumir 
que el mercado ya tiene priceado el evento positivo y argumentar por qué podría 
NO ser buena entrada en este momento. Sé directo y conciso.'''
}

# ── Consultar un agente ──────────────────────────────
def consult_agent(persona_name, persona_prompt, context):
    prompt = f'''{persona_prompt}

Contexto del análisis:
{context}

Responde ÚNICAMENTE con este JSON exacto, sin texto adicional:
{{"accion": "COMPRAR", "probabilidad": 75, "razon": "tu razon aqui"}}

Donde:
- accion: solo puede ser COMPRAR, VENDER o MANTENER
- probabilidad: número del 0 al 100 indicando tu confianza
- razon: máximo 2 oraciones explicando tu decisión'''

    try:
        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=200,
            messages=[{'role': 'user', 'content': prompt}]
        )
        raw = msg.content[0].text.strip()
        # Limpiar posibles markdown code blocks
        raw = raw.replace('```json', '').replace('```', '').strip()
        return json.loads(raw)
    except Exception as e:
        print(f'  [ERROR agente {persona_name}]: {e}')
        return {'accion': 'MANTENER', 'probabilidad': 50, 'razon': 'Error en análisis'}

# ── Swarm completo ───────────────────────────────────
def get_swarm_signal(opportunity):
    context = f'''Empresa: {opportunity["ticker"]} — {opportunity["company"]}
Catalizadores detectados: {", ".join(opportunity["reasons"])}
Ensayos Fase III activos: {sum(1 for t in opportunity["trials"] if "PHASE3" in t.get("phase", ""))}
Ensayos Fase II activos: {sum(1 for t in opportunity["trials"] if "PHASE2" in t.get("phase", ""))}
Precio actual: ${opportunity["price_data"]["current"] if opportunity["price_data"] else "N/A"}
Cambio últimos 30 días: {opportunity["price_data"]["change_30d"] if opportunity["price_data"] else "N/A"}%
Volumen relativo: {opportunity["price_data"]["volume_ratio"] if opportunity["price_data"] else "N/A"}x el promedio'''

    print(f'\n  Consultando swarm para {opportunity["ticker"]}...')
    results = []
    for name, prompt in PERSONAS.items():
        result = consult_agent(name, prompt, context)
        results.append(result)
        print(f'    {name:20s}: {result["accion"]:8s} ({result["probabilidad"]}%)')

    # Calcular consenso
    avg_prob     = sum(r['probabilidad'] for r in results) / len(results)
    votes        = [r['accion'] for r in results]
    accion_final = max(set(votes), key=votes.count)
    votos_favor  = votes.count(accion_final)

    # Edge = probabilidad promedio vs 50% base
    edge = round((avg_prob / 100) - 0.50, 3)

    print(f'    {"CONSENSO":20s}: {accion_final:8s} ({avg_prob:.1f}%) — votos {votos_favor}/5 — edge {edge:.3f}')

    return {
        'accion':      accion_final,
        'probabilidad': round(avg_prob, 1),
        'edge':        edge,
        'votos':       f'{votos_favor}/5',
        'detalle':     results
    }

# ── Test ─────────────────────────────────────────────
if __name__ == '__main__':
    print('=== Test Multi Persona ===')
    # Oportunidad de prueba con ACAD
    test_opp = {
        'ticker':     'ACAD',
        'company':    'ACADIA Pharmaceuticals',
        'reasons':    ['1 ensayo(s) Fase III', '5 ensayo(s) Fase II', 'Precio estable 30d'],
        'trials':     [{'phase': 'PHASE3'}] + [{'phase': 'PHASE2'}] * 5,
        'price_data': {'current': 15.20, 'change_30d': -3.5, 'volume_ratio': 1.2}
    }
    signal = get_swarm_signal(test_opp)
    print(f'\nSeñal final: {signal["accion"]} | Edge: {signal["edge"]} | Votos: {signal["votos"]}')
    print('=== OK ===')