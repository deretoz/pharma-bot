# bot.py
import os
import csv
import schedule
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

from alpaca_bridge import (get_account, is_market_open,
                           place_order, close_position, get_positions)
from pharma_scanner import scan_opportunities
from Multi_Person import get_swarm_signal
from kelly import calculate_position
from Notifier import notify_signal, notify_stop_loss, notify_start, notify_cycle, send

load_dotenv()

# ── Logging ──────────────────────────────────────────
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    filename='logs/bot.log',
    level=logging.INFO,
    format='%(asctime)s — %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def log(msg):
    print(msg)
    logging.info(msg)

# ── Guardar trade en CSV ─────────────────────────────
def save_trade(opp, signal, position):
    filepath = 'logs/trades.csv'
    file_exists = os.path.exists(filepath)

    with open(filepath, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'fecha', 'hora', 'ticker', 'empresa',
            'accion', 'edge', 'probabilidad', 'votos',
            'precio', 'monto', 'pct_capital', 'modo'
        ])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            'fecha':       datetime.now().strftime('%Y-%m-%d'),
            'hora':        datetime.now().strftime('%H:%M:%S'),
            'ticker':      opp['ticker'],
            'empresa':     opp['company'],
            'accion':      signal['accion'],
            'edge':        signal['edge'],
            'probabilidad':signal['probabilidad'],
            'votos':       signal['votos'],
            'precio':      opp['price_data']['current'] if opp['price_data'] else 0,
            'monto':       position['dollar_amount'],
            'pct_capital': position['pct_bankroll'],
            'modo':        'PAPER' if os.getenv('DRY_RUN') == 'True' else 'REAL'
        })

# ── Stop losses ──────────────────────────────────────
def check_stop_losses():
    stop_pct = float(os.getenv('STOP_LOSS_PCT', -0.15)) * 100
    for pos in get_positions():
        if pos['pnl_pct'] < stop_pct:
            log(f'STOP LOSS: {pos["ticker"]} en {pos["pnl_pct"]:.1f}%')
            close_position(pos['ticker'])
            notify_stop_loss(pos['ticker'], pos['pnl_pct'])

# ── Ciclo principal ───────────────────────────────────
def run_cycle():
    try:
        log(f'\n{"="*50}')
        log(f'Ciclo iniciado: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

        if not is_market_open():
            log('Mercado cerrado — esperando próximo ciclo')
            return

        check_stop_losses()

        account = get_account()
        log(f'Balance: ${account["cash"]:,.2f} | Portfolio: ${account["portfolio_value"]:,.2f}')

        opportunities = scan_opportunities()
        log(f'Oportunidades encontradas: {len(opportunities)}')

        if not opportunities:
            log('Sin oportunidades en este ciclo')
            notify_cycle(0, account['cash'])
            return

        trades_ejecutados = 0
        for opp in opportunities[:3]:
            log(f'\nAnalizando {opp["ticker"]} (score={opp["score"]})...')
            signal = get_swarm_signal(opp)

            min_edge = float(os.getenv('MIN_EDGE', 0.05))
            if signal['edge'] < min_edge:
                log(f'  Edge insuficiente ({signal["edge"]}) — skip')
                continue

            position = calculate_position(
                bankroll=account['cash'],
                edge=signal['edge']
            )

            if position['dollar_amount'] == 0:
                log(f'  Posición $0 — skip')
                continue

            log(f'  Señal: {signal["accion"]} | Edge: {signal["edge"]} | Monto: ${position["dollar_amount"]}')

            # Guardar en CSV siempre
            save_trade(opp, signal, position)

            if os.getenv('DRY_RUN') == 'True':
                log(f'  [DRY RUN] {signal["accion"]} {opp["ticker"]} ${position["dollar_amount"]}')
            else:
                result = place_order(opp['ticker'], signal['accion'], position['dollar_amount'])
                log(f'  Orden ejecutada: {result}')

            notify_signal(opp, signal, position)
            trades_ejecutados += 1

        log(f'Ciclo completado: {datetime.now().strftime("%H:%M:%S")}')
        notify_cycle(trades_ejecutados, account['cash'])

    except Exception as e:
        log(f'[ERROR ciclo]: {e} — reintentando en 30 minutos')
        send(f'⚠️ *Error en Pharma Bot*\n`{str(e)[:200]}`\nReintentando en 30 minutos')

# ── Main ─────────────────────────────────────────────
if __name__ == '__main__':
    log('🤖 Pharma Bot iniciando...')
    notify_start()

    run_cycle()

    schedule.every(30).minutes.do(run_cycle)

    log('Scheduler activo — ciclo cada 30 minutos')
    while True:
        schedule.run_pending()
        time.sleep(60)