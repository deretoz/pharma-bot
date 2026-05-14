# kelly.py

def calculate_position(bankroll, edge, min_edge=0.05,
                       max_pct=0.05, kelly_fraction=0.25):
    """
    Calcula el tamaño óptimo de posición usando Kelly Criterion.
    
    bankroll      : capital disponible en USD
    edge          : ventaja estimada (ej: 0.10 = 10% sobre el 50% base)
    min_edge      : edge mínimo para operar (default 5%)
    max_pct       : máximo % del bankroll por trade (default 5%)
    kelly_fraction: fracción de Kelly a usar (default 1/4 Kelly)
    """
    if edge < min_edge:
        return {
            'dollar_amount': 0,
            'pct_bankroll':  0,
            'kelly_raw':     0,
            'motivo':        f'Edge {edge:.3f} menor al mínimo {min_edge}'
        }

    # Kelly completo para apuesta binaria
    kelly_full = edge * 2

    # Kelly conservador (1/4 del Kelly completo)
    kelly_safe = kelly_full * kelly_fraction

    # Nunca superar el máximo por trade
    position_pct    = min(kelly_safe, max_pct)
    dollar_amount   = bankroll * position_pct

    return {
        'dollar_amount': round(dollar_amount, 2),
        'pct_bankroll':  round(position_pct * 100, 2),
        'kelly_raw':     round(kelly_full * 100, 2),
        'motivo':        f'Kelly {kelly_full*100:.1f}% → seguro {position_pct*100:.1f}%'
    }

# ── Test ─────────────────────────────────────────────
if __name__ == '__main__':
    print('=== Test Kelly Criterion ===')

    casos = [
        {'bankroll': 100000, 'edge': 0.03, 'desc': 'Edge insuficiente'},
        {'bankroll': 100000, 'edge': 0.08, 'desc': 'Edge moderado'},
        {'bankroll': 100000, 'edge': 0.15, 'desc': 'Edge alto'},
        {'bankroll': 100000, 'edge': 0.25, 'desc': 'Edge muy alto'},
        {'bankroll':    200, 'edge': 0.10, 'desc': 'Capital real pequeño ($200)'},
    ]

    for c in casos:
        result = calculate_position(c['bankroll'], c['edge'])
        print(f"\n  {c['desc']}")
        print(f"    Bankroll: ${c['bankroll']:,.2f} | Edge: {c['edge']*100:.0f}%")
        print(f"    Monto:    ${result['dollar_amount']:,.2f} ({result['pct_bankroll']}% del capital)")
        print(f"    Detalle:  {result['motivo']}")

    print('\n=== OK ===')