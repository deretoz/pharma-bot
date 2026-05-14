# Notifier.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN   = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# ── Enviar mensaje base ──────────────────────────────
def send(msg):
    try:
        url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
        requests.post(url, json={
            'chat_id':    CHAT_ID,
            'text':       msg,
            'parse_mode': 'Markdown'
        }, timeout=10)
    except Exception as e:
        print(f'[ERROR Telegram]: {e}')

# ── Notificación de señal ────────────────────────────
def notify_signal(opp, signal, position):
    emoji = '🟢' if signal['accion'] == 'COMPRAR' else \
            '🔴' if signal['accion'] == 'VENDER'  else '⚪'
    modo  = '📝 PAPER' if os.getenv('DRY_RUN') == 'True' else '💸 REAL'
    msg   = f'''{emoji} *{signal["accion"]} {opp["ticker"]}*
🏢 {opp["company"]}
💰 Precio: ${opp["price_data"]["current"]}
📊 Edge: {signal["edge"]*100:.1f}% | Votos: {signal["votos"]}
🔬 {", ".join(opp["reasons"][:2])}
💵 Monto: ${position["dollar_amount"]} ({position["pct_bankroll"]}% capital)
⚙️ Modo: {modo}'''
    send(msg)

# ── Notificación de stop loss ────────────────────────
def notify_stop_loss(ticker, pnl_pct):
    msg = f'''🛑 *STOP LOSS ejecutado*
📉 {ticker} cerrado en {pnl_pct:.1f}%
⚠️ Posición liquidada automáticamente'''
    send(msg)

# ── Notificación de inicio ───────────────────────────
def notify_start():
    modo = '📝 PAPER TRADING' if os.getenv('DRY_RUN') == 'True' else '💸 TRADING REAL'
    msg  = f'''🤖 *Pharma Bot iniciado*
✅ Escaneando mercado cada 30 minutos
📋 Modo: {modo}'''
    send(msg)

# ── Notificación de ciclo ────────────────────────────
def notify_cycle(n_opps, balance):
    msg = f'''🔄 *Ciclo completado*
🔍 Oportunidades encontradas: {n_opps}
💼 Balance actual: ${balance:,.2f}'''
    send(msg)

# ── Test ─────────────────────────────────────────────
if __name__ == '__main__':
    print('=== Test Notifier ===')
    send('🧪 *Test Pharma Bot* — Conexión Telegram OK ✅')
    print('Mensaje enviado a Telegram.')
    print('=== OK ===')