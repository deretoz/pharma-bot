# rl_data_builder.py
# Descarga datos históricos de Alpaca y construye dataset para RL

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca_bridge import data_client
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

load_dotenv()

WATCHLIST = {
    'ACAD': 'ACADIA Pharmaceuticals',
    'ARWR': 'Arrowhead Pharmaceuticals',
    'RCUS': 'Arcus Biosciences',
    'AGEN': 'Agenus Inc',
    'SAVA': 'Cassava Sciences',
}

YEARS_BACK = 2  # 2 años de datos históricos

# ── Descargar datos históricos ───────────────────────
def download_historical_data(ticker, years=2):
    try:
        print(f'  Descargando {ticker} — {years} años...')
        start = datetime.now() - timedelta(days=years * 365)
        req   = StockBarsRequest(
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
        bars['ticker'] = ticker
        print(f'  ✓ {ticker}: {len(bars)} días descargados')
        return bars
    except Exception as e:
        print(f'  [ERROR {ticker}]: {e}')
        return None

# ── Calcular features técnicas ───────────────────────
def build_features(bars):
    df = bars.copy()

    # Precio normalizado (z-score rolling 30d)
    df['precio']      = df['close']
    df['precio_norm'] = (
        (df['close'] - df['close'].rolling(30).mean())
        / (df['close'].rolling(30).std() + 1e-8)
    ).clip(-5, 5)

    # Cambio de precio
    df['change_1d']  = df['close'].pct_change(1)  * 100
    df['change_5d']  = df['close'].pct_change(5)  * 100
    df['change_30d'] = df['close'].pct_change(30) * 100

    # Volumen relativo
    df['vol_ma20']    = df['volume'].rolling(20).mean()
    df['volume_ratio']= (df['volume'] / (df['vol_ma20'] + 1)).clip(0, 10)

    # Volatilidad
    df['volatility'] = df['close'].pct_change().rolling(20).std() * 100

    # Probabilidades simuladas del swarm
    # (se reemplazarán con datos reales cuando tengamos suficientes)
    np.random.seed(42)
    n = len(df)
    base_p = 0.55 + df['change_30d'].fillna(0).clip(-20, 20) / 200

    df['p_success'] = (base_p + np.random.normal(0, 0.05, n)).clip(0.3, 0.8)
    df['p_failure'] = ((1 - df['p_success']) * 0.6).clip(0.1, 0.5)
    df['p_neutral'] = (1 - df['p_success'] - df['p_failure']).clip(0.05, 0.4)

    # Normalizar para que sumen 1
    total = df['p_success'] + df['p_failure'] + df['p_neutral']
    df['p_success'] /= total
    df['p_failure'] /= total
    df['p_neutral']  /= total

    # Target: subió > 10% en los próximos 30 días
    df['future_return'] = df['close'].shift(-30).pct_change(30) * 100 # noqa
    df['target']        = (df['future_return'] > 10).astype(int)

    # Limpiar NaNs
    df = df.dropna().reset_index(drop=True)

    return df

# ── Combinar con trades reales del bot ───────────────
def merge_with_real_trades(df, trades_csv='logs/trades.csv'):
    if not os.path.exists(trades_csv):
        print('  Sin trades reales aún — usando solo datos históricos')
        return df

    trades = pd.read_csv(trades_csv)
    trades['fecha'] = pd.to_datetime(trades['fecha'])

    print(f'  Mergeando {len(trades)} trades reales del bot...')

    # Para cada trade real, actualizar p_success/p_failure en el dataset
    for _, trade in trades.iterrows():
        mask = (
            (df['ticker'] == trade['ticker']) &
            (df['timestamp'].dt.date == trade['fecha'].date())
        )
        if mask.any():
            df.loc[mask, 'p_success'] = trade['edge'] + 0.5
            df.loc[mask, 'p_failure'] = max(0.1, 0.5 - trade['edge'])

    print('  ✓ Trades reales integrados')
    return df

# ── Main ─────────────────────────────────────────────
if __name__ == '__main__':
    print('=== RL Data Builder ===')
    print(f'Descargando {len(WATCHLIST)} empresas — {YEARS_BACK} años\n')

    all_data = []

    for ticker in WATCHLIST:
        bars = download_historical_data(ticker, YEARS_BACK)
        if bars is not None:
            df = build_features(bars)
            df = merge_with_real_trades(df)
            all_data.append(df)

    if not all_data:
        print('Error: sin datos')
        exit()

    # Combinar todos los tickers
    full_df = pd.concat(all_data, ignore_index=True)
    full_df = full_df.sort_values(['ticker', 'timestamp']).reset_index(drop=True)

    # Guardar dataset
    os.makedirs('data', exist_ok=True)
    full_df.to_csv('data/rl_dataset.csv', index=False)

    print(f'\n=== Dataset listo ===')
    print(f'Total filas:    {len(full_df)}')
    print(f'Empresas:       {full_df["ticker"].nunique()}')
    print(f'Período:        {full_df["timestamp"].min().date()} → {full_df["timestamp"].max().date()}')
    print(f'Features:       {[c for c in full_df.columns if c not in ["timestamp","ticker"]]}')
    print(f'Target positivo:{full_df["target"].mean()*100:.1f}% de los días')
    print(f'Guardado en:    data/rl_dataset.csv')
    print('=== OK ===')