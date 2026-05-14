# pharma_scanner.py
import os
import requests
from dotenv import load_dotenv
from alpaca_bridge import get_price_data

load_dotenv()

# ── Watchlist ────────────────────────────────────────
WATCHLIST = {
    'ACAD': 'ACADIA Pharmaceuticals',
    'SAVA': 'Cassava Sciences',
    'AGEN': 'Agenus Inc',
    'ARWR': 'Arrowhead Pharmaceuticals',
    'RCUS': 'Arcus Biosciences',
    'FATE': 'Fate Therapeutics',
    'KALA': 'Kala Bio',
    'TNYA': 'Tenaya Therapeutics',
    'CABA': 'Cabaletta Bio',
    'RVNC': 'Revance Therapeutics'
}

# ── ClinicalTrials API ───────────────────────────────
def get_clinical_trials(company_name):
    try:
        r = requests.get(
            'https://clinicaltrials.gov/api/v2/studies',
            params={
                'query.spons': company_name,
                'filter.overallStatus': 'ACTIVE_NOT_RECRUITING,RECRUITING',
                'pageSize': 20,
                'format': 'json'
            },
            timeout=10
        )
        if r.status_code != 200:
            return []
        catalysts = []
        for s in r.json().get('studies', []):
            proto  = s.get('protocolSection', {})
            design = proto.get('designModule', {})
            phases = design.get('phases', [])
            status = proto.get('statusModule', {})
            title  = proto.get('identificationModule', {}).get('briefTitle', '')
            end_date = status.get('primaryCompletionDateStruct', {}).get('date', '')
            if any(p in phases for p in ['PHASE2', 'PHASE3']):
                catalysts.append({
                    'phase':    phases[0] if phases else 'UNKNOWN',
                    'end_date': end_date,
                    'status':   status.get('overallStatus', ''),
                    'title':    title
                })
        return catalysts
    except Exception as e:
        print(f'[ERROR ClinicalTrials {company_name}]: {e}')
        return []

# ── OpenFDA API ──────────────────────────────────────
def get_fda_history(company_name):
    try:
        r = requests.get(
            'https://api.fda.gov/drug/drugsfda.json',
            params={
                'search': f'sponsor_name:"{company_name}"',
                'limit': 10
            },
            timeout=10
        )
        if r.status_code != 200:
            return []
        results = r.json().get('results', [])
        return [{
            'drug':   res.get('brand_name', ''),
            'status': res.get('submissions', [{}])[0].get('submission_type', ''),
            'date':   res.get('submissions', [{}])[0].get('submission_date', '')
        } for res in results]
    except Exception as e:
        print(f'[ERROR FDA {company_name}]: {e}')
        return []

# ── Scoring ──────────────────────────────────────────
def score_opportunity(ticker, trials, fda_history, price_data):
    score   = 0
    reasons = []

    # Contar fases únicas (no sumar por cada ensayo)
    has_phase3 = any('PHASE3' in t.get('phase', '') for t in trials)
    has_phase2 = any('PHASE2' in t.get('phase', '') for t in trials)
    phase3_count = sum(1 for t in trials if 'PHASE3' in t.get('phase', ''))
    phase2_count = sum(1 for t in trials if 'PHASE2' in t.get('phase', ''))

    if has_phase3:
        score += 40
        reasons.append(f'{phase3_count} ensayo(s) Fase III')
    if has_phase2:
        score += 20
        reasons.append(f'{phase2_count} ensayo(s) Fase II')

    if price_data:
        if price_data['volume_ratio'] > 2:
            score += 15
            reasons.append(f'Volumen {price_data["volume_ratio"]}x promedio')
        if abs(price_data['change_30d']) < 20:
            score += 10
            reasons.append('Precio estable 30d')

    approvals = [f for f in fda_history if 'AP' in f.get('status', '')]
    if approvals:
        score += 15
        reasons.append('Historial FDA positivo')

    return score, reasons
# ── Scanner principal ────────────────────────────────
def scan_opportunities():
    print('Escaneando watchlist...')
    opportunities = []

    for ticker, company in WATCHLIST.items():
        print(f'  Analizando {ticker}...')
        trials     = get_clinical_trials(company)
        fda        = get_fda_history(company)
        price_data = get_price_data(ticker)
        score, reasons = score_opportunity(ticker, trials, fda, price_data)

        if score >= 40:
            opportunities.append({
                'ticker':     ticker,
                'company':    company,
                'score':      score,
                'reasons':    reasons,
                'trials':     trials,
                'price_data': price_data
            })
            print(f'  ✓ {ticker} score={score} — {", ".join(reasons)}')
        else:
            print(f'  ✗ {ticker} score={score} — insuficiente')

    return sorted(opportunities, key=lambda x: x['score'], reverse=True)

# ── Test ─────────────────────────────────────────────
if __name__ == '__main__':
    print('=== Test Pharma Scanner ===')
    opps = scan_opportunities()
    print(f'\n{len(opps)} oportunidades encontradas:')
    for o in opps:
        print(f'  {o["ticker"]} | score={o["score"]} | {", ".join(o["reasons"])}')
    print('=== OK ===')