# backtest.py
import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca_bridge import data_client
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

load_dotenv()

# ── Configuración ────────────────────────────────────
WATCHLIST = {
    'ACAD': 'ACADIA Pharmaceuticals',
    'SAVA': 'Cassava Sciences',
    'AGEN': 'Agenus Inc',
    'ARWR': 'Arrowhead Pharmaceuticals',
    'RCUS': 'Arcus Biosciences',
}

MESES_ATRAS     = 12
HOLD_DAYS       = 20   # antes 30 — salir antes
STOP_LOSS_PCT   = -10  # antes -15 — cortar pérdidas más rápido
TAKE_PROFIT_PCT = 20   # antes 25 — asegurar ganancias antes

# ── Obtener historial de precios ─────────────────────
def get_historical_prices(ticker, months=12):
    try:
        start = datetime.now() - timedelta(days=months * 30)
        req = StockBarsRequest(
            symbol_or_symbols=ticker,
            timeframe=TimeFrame.Day,
            start=start
        )
        bars = data_client.get_stock_bars(req).df
        bars = bars.reset_index()
        if 'symbol' in bars.columns:
            bars = bars[bars['symbol'] == ticker]
        bars = bars[['timestamp', 'close', 'volume']].copy()
        bars['timestamp'] = pd.to_datetime(bars['timestamp']).dt.tz_localize(None)
        bars = bars.sort_values('timestamp').reset_index(drop=True)
        return bars
    except Exception as e:
        print(f'  [ERROR historial {ticker}]: {e}')
        return None

# ── Detectar señales históricas ──────────────────────
def detect_signals(bars):
    """
    Detecta señales de compra basadas en:
    - Volumen inusual (2x el promedio móvil de 20 días)
    - Precio estable en los últimos 10 días (no ya pumpeado)
    """
    signals = []
    if bars is None or len(bars) < 30:
        return signals

    bars['vol_ma20']      = bars['volume'].rolling(20).mean()
    bars['vol_ratio']     = bars['volume'] / bars['vol_ma20']
    bars['price_change_10d'] = bars['close'].pct_change(10) * 100

    for i in range(20, len(bars) - HOLD_DAYS):
        row = bars.iloc[i]
        # Señal: volumen inusual + precio no sobrecomprado
        if (row['vol_ratio'] > 1.8 and
                abs(row['price_change_10d']) < 15):
            signals.append({
                'date':        row['timestamp'],
                'price_entry': row['close'],
                'vol_ratio':   round(row['vol_ratio'], 2),
                'idx':         i
            })
    return signals

# ── Simular cada trade ───────────────────────────────
def simulate_trades(bars, signals, ticker):
    trades = []
    used_indices = set()

    for sig in signals:
        idx = sig['idx']
        # Evitar señales solapadas (esperar HOLD_DAYS entre trades)
        if any(abs(idx - u) < HOLD_DAYS for u in used_indices):
            continue

        entry_price = sig['price_entry']
        exit_price  = None
        exit_date   = None
        exit_reason = None

        # Simular los siguientes HOLD_DAYS días
        for j in range(1, HOLD_DAYS + 1):
            if idx + j >= len(bars):
                break
            future = bars.iloc[idx + j]
            pct_change = ((future['close'] - entry_price) / entry_price) * 100

            # Stop loss
            if pct_change <= STOP_LOSS_PCT:
                exit_price  = future['close']
                exit_date   = future['timestamp']
                exit_reason = 'STOP LOSS'
                break
            # Take profit
            if pct_change >= TAKE_PROFIT_PCT:
                exit_price  = future['close']
                exit_date   = future['timestamp']
                exit_reason = 'TAKE PROFIT'
                break
            # Fin del período
            if j == HOLD_DAYS:
                exit_price  = future['close']
                exit_date   = future['timestamp']
                exit_reason = 'TIEMPO'

        if exit_price:
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            trades.append({
                'ticker':      ticker,
                'entry_date':  sig['date'].strftime('%Y-%m-%d'),
                'exit_date':   exit_date.strftime('%Y-%m-%d'),
                'entry_price': round(entry_price, 2),
                'exit_price':  round(exit_price, 2),
                'pnl_pct':     round(pnl_pct, 2),
                'vol_ratio':   sig['vol_ratio'],
                'exit_reason': exit_reason,
                'resultado':   '✅ WIN' if pnl_pct > 0 else '❌ LOSS'
            })
            used_indices.add(idx)

    return trades

# ── Métricas finales ─────────────────────────────────
def calculate_metrics(all_trades):
    if not all_trades:
        return None

    df = pd.DataFrame(all_trades)
    wins        = df[df['pnl_pct'] > 0]
    losses      = df[df['pnl_pct'] <= 0]
    win_rate    = len(wins) / len(df) * 100
    avg_win     = wins['pnl_pct'].mean() if len(wins) > 0 else 0
    avg_loss    = losses['pnl_pct'].mean() if len(losses) > 0 else 0
    avg_return  = df['pnl_pct'].mean()

    # Simular curva de capital ($10,000 inicial)
    capital     = 10000
    capitals    = [capital]
    for _, row in df.iterrows():
        capital = capital * (1 + row['pnl_pct'] / 100)
        capitals.append(capital)

    peak        = pd.Series(capitals).cummax()
    drawdown    = ((pd.Series(capitals) - peak) / peak * 100).min()
    total_return = ((capitals[-1] - 10000) / 10000) * 100

    return {
        'total_trades':  len(df),
        'wins':          len(wins),
        'losses':        len(losses),
        'win_rate':      round(win_rate, 1),
        'avg_win':       round(avg_win, 2),
        'avg_loss':      round(avg_loss, 2),
        'avg_return':    round(avg_return, 2),
        'total_return':  round(total_return, 1),
        'max_drawdown':  round(drawdown, 1),
        'capital_final': round(capitals[-1], 2),
        'df':            df
    }

# ── Main ─────────────────────────────────────────────
if __name__ == '__main__':
    print(f'=== Backtest {MESES_ATRAS} meses ===')
    print(f'Stop loss: {STOP_LOSS_PCT}% | Take profit: {TAKE_PROFIT_PCT}% | Hold: {HOLD_DAYS} días\n')

    all_trades = []

    for ticker, company in WATCHLIST.items():
        print(f'Procesando {ticker} — {company}...')
        bars    = get_historical_prices(ticker, MESES_ATRAS)
        signals = detect_signals(bars)
        trades  = simulate_trades(bars, signals, ticker)
        all_trades.extend(trades)
        print(f'  Señales detectadas: {len(signals)} | Trades simulados: {len(trades)}')

    print(f'\n{"="*50}')
    metrics = calculate_metrics(all_trades)

    if not metrics:
        print('Sin trades suficientes para calcular métricas')
    else:
        print(f'RESULTADOS GLOBALES ({MESES_ATRAS} meses)')
        print(f'{"="*50}')
        print(f'Total trades:    {metrics["total_trades"]}')
        print(f'Wins:            {metrics["wins"]} | Losses: {metrics["losses"]}')
        print(f'Win rate:        {metrics["win_rate"]}%')
        print(f'Retorno promedio:{metrics["avg_return"]}% por trade')
        print(f'Promedio win:    +{metrics["avg_win"]}%')
        print(f'Promedio loss:   {metrics["avg_loss"]}%')
        print(f'Retorno total:   {metrics["total_return"]}%')
        print(f'Max drawdown:    {metrics["max_drawdown"]}%')
        print(f'Capital inicial: $10,000')
        print(f'Capital final:   ${metrics["capital_final"]:,.2f}')
        print(f'{"="*50}')

        # Veredicto
        if metrics['win_rate'] >= 52 and metrics['max_drawdown'] > -35:
            print('✅ Sistema con edge — viable para paper trading')
        elif metrics['win_rate'] >= 50:
            print('⚠️  Sistema marginal — ajustar parámetros')
        else:
            print('❌ Sin edge suficiente — revisar lógica')

        # Guardar resultados
        os.makedirs('logs', exist_ok=True)
        metrics['df'].to_csv('logs/backtest_results.csv', index=False)
        print(f'\nResultados guardados en logs/backtest_results.csv')

    print('=== FIN ===')