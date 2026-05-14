# alpaca_bridge.py
import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

load_dotenv()

# Clientes Alpaca
trading = TradingClient(
    api_key=os.getenv('ALPACA_API_KEY'),
    secret_key=os.getenv('ALPACA_SECRET_KEY'),
    paper=True
)

data_client = StockHistoricalDataClient(
    api_key=os.getenv('ALPACA_API_KEY'),
    secret_key=os.getenv('ALPACA_SECRET_KEY')
)

# ── Cuenta ──────────────────────────────────────────
def get_account():
    acc = trading.get_account()
    return {
        'cash': float(acc.cash),
        'portfolio_value': float(acc.portfolio_value),
        'buying_power': float(acc.buying_power)
    }

def is_market_open():
    return trading.get_clock().is_open

# ── Precios ─────────────────────────────────────────
def get_price_data(ticker):
    try:
        req = StockBarsRequest(
            symbol_or_symbols=ticker,
            timeframe=TimeFrame.Day,
            start=datetime.now() - timedelta(days=30)
        )
        bars = data_client.get_stock_bars(req).df
        if bars.empty:
            return None
        current    = float(bars['close'].iloc[-1])
        change_30d = ((current - float(bars['close'].iloc[0]))
                      / float(bars['close'].iloc[0])) * 100
        avg_vol    = bars['volume'].mean()
        last_vol   = float(bars['volume'].iloc[-1])
        return {
            'current':      round(current, 2),
            'change_30d':   round(change_30d, 2),
            'volume_ratio': round(last_vol / avg_vol, 2)
        }
    except Exception as e:
        print(f'[ERROR get_price_data {ticker}]: {e}')
        return None

# ── Órdenes ─────────────────────────────────────────
def place_order(ticker, side, dollar_amount):
    price_data = get_price_data(ticker)
    if not price_data:
        return None
    price = price_data['current']
    qty   = round(dollar_amount / price, 6)
    if qty < 0.001:
        return None
    req = LimitOrderRequest(
        symbol=ticker,
        qty=qty,
        side=OrderSide.BUY if side == 'COMPRAR' else OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
        limit_price=round(price * 1.002, 2)
    )
    order = trading.submit_order(req)
    return {'order_id': str(order.id), 'qty': qty, 'price': price}

def close_position(ticker):
    try:
        trading.close_position(ticker)
        return True
    except Exception as e:
        print(f'[ERROR close_position {ticker}]: {e}')
        return False

def get_positions():
    positions = trading.get_all_positions()
    return [{
        'ticker':        p.symbol,
        'qty':           float(p.qty),
        'current_price': float(p.current_price),
        'pnl_pct':       float(p.unrealized_plpc) * 100
    } for p in positions]

# ── Test ─────────────────────────────────────────────
if __name__ == '__main__':
    print('=== Test Alpaca Bridge ===')
    acc = get_account()
    print(f'Cash:      ${acc["cash"]:,.2f}')
    print(f'Portfolio: ${acc["portfolio_value"]:,.2f}')
    print(f'Mercado abierto: {is_market_open()}')
    price = get_price_data('ACAD')
    if price:
        print(f'ACAD precio:    ${price["current"]}')
        print(f'ACAD cambio 30d: {price["change_30d"]}%')
        print(f'ACAD volumen:    {price["volume_ratio"]}x')
    print('=== OK ===')