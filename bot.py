# bot.py
import os
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
from Notifier import notify_signal, notify_stop_loss, notify_start, notify_cycle

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
    log(f'\n{"="*50}')
    log(f'Ciclo iniciado: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

    # Solo opera si el mercado está abierto
    if not is_market_open():
        log('Mercado cerrado — esperando próximo ciclo')
        return

    # Revisar stop losses primero
    check_stop_losses()

    # Balance actual
    account = get_account()
    log(f'Balance: ${account["cash"]:,.2f} | Portfolio: ${account["portfolio_value"]:,.2f}')

    # Escanear oportunidades
    opportunities = scan_opportunities()
    log(f'Oportunidades encontradas: {len(opportunities)}')

    notify_cycle(len(opportunities), account['cash'])

    if not opportunities:
        log('Sin oportunidades en este ciclo')
        return

    # Analizar top 3 con el swarm
    for opp in opportunities[:3]:
        log(f'\nAnalizando {opp["ticker"]} (score={opp["score"]})...')
        signal = get_swarm_signal(opp)

        # Solo actuar si hay edge suficiente
        min_edge = float(os.getenv('MIN_EDGE', 0.05))
        if signal['edge'] < min_edge:
            log(f'  Edge insuficiente ({signal["edge"]}) — skip')
            continue

        # Calcular tamaño de posición
        position = calculate_position(
            bankroll=account['cash'],
            edge=signal['edge']
        )

        if position['dollar_amount'] == 0:
            log(f'  Posición $0 — skip')
            continue

        log(f'  Señal: {signal["accion"]} | Edge: {signal["edge"]} | Monto: ${position["dollar_amount"]}')

        # Ejecutar o simular
        if os.getenv('DRY_RUN') == 'True':
            log(f'  [DRY RUN] {signal["accion"]} {opp["ticker"]} ${position["dollar_amount"]}')
        else:
            result = place_order(opp['ticker'], signal['accion'], position['dollar_amount'])
            log(f'  Orden ejecutada: {result}')

        notify_signal(opp, signal, position)

    log(f'Ciclo completado: {datetime.now().strftime("%H:%M:%S")}')

# ── Main ─────────────────────────────────────────────
if __name__ == '__main__':
    log('🤖 Pharma Bot iniciando...')
    notify_start()

    # Primer ciclo inmediato
    run_cycle()

    # Luego cada 30 minutos
    schedule.every(30).minutes.do(run_cycle)

    log('Scheduler activo — ciclo cada 30 minutos')
    while True:
        schedule.run_pending()
        time.sleep(60)