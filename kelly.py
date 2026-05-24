# kelly.py — v2
# Usa distribución de probabilidad del Swarm v2

def calculate_position(bankroll, edge, p_success=None,
                       p_failure=None, min_edge=0.05,
                       max_pct=0.05, kelly_fraction=0.25):
    if edge < min_edge:
        return {
            'dollar_amount': 0,
            'pct_bankroll':  0,
            'kelly_raw':     0,
            'motivo':        f'Edge {edge:.3f} menor al mínimo {min_edge}'
        }

    # Si tenemos distribución completa, usar Kelly exacto
    # f* = (p*b - q) / b  donde b = odds, p = p_success, q = p_failure
    if p_success is not None and p_failure is not None:
        b = p_success / max(p_failure, 0.01)  # odds implícitas
        q = p_failure
        kelly_full = (p_success * b - q) / b
        kelly_full = max(0, kelly_full)  # nunca negativo
    else:
        kelly_full = edge * 2

    kelly_safe    = kelly_full * kelly_fraction
    position_pct  = min(kelly_safe, max_pct)
    dollar_amount = bankroll * position_pct

    return {
        'dollar_amount': round(dollar_amount, 2),
        'pct_bankroll':  round(position_pct * 100, 2),
        'kelly_raw':     round(kelly_full * 100, 2),
        'motivo':        f'Kelly {kelly_full*100:.1f}% → seguro {position_pct*100:.1f}%'
    }

if __name__ == '__main__':
    print('=== Test Kelly v2 ===')
    casos = [
        {'p_success': 0.662, 'p_failure': 0.186, 'desc': 'ARWR — swarm v2'},
        {'p_success': 0.550, 'p_failure': 0.300, 'desc': 'Señal moderada'},
        {'p_success': 0.480, 'p_failure': 0.350, 'desc': 'Sin edge — no operar'},
    ]
    for c in casos:
        edge = round(c['p_success'] - 0.50, 3)
        r = calculate_position(100000, edge,
                               p_success=c['p_success'],
                               p_failure=c['p_failure'])
        print(f"\n  {c['desc']}")
        print(f"    p_success={c['p_success']} | edge={edge}")
        print(f"    Monto: ${r['dollar_amount']:,.2f} | {r['motivo']}")
    print('\n=== OK ===')