[README.md](https://github.com/user-attachments/files/27737531/README.md)
# 🤖 Pharma Bot

Bot de trading automatizado especializado en acciones farmacéuticas y biotecnológicas del NASDAQ. Utiliza inteligencia artificial para analizar datos científicos en tiempo real (ensayos clínicos, aprobaciones FDA) y generar señales de compra/venta con gestión de riesgo automática.

---

## ¿Cómo funciona?

El bot corre un ciclo cada 30 minutos durante el horario de mercado (9:30am–4:00pm ET). En cada ciclo:

1. **Escanea** la watchlist de empresas farmacéuticas buscando catalizadores científicos activos (ensayos Fase II/III, historial FDA, volumen inusual)
2. **Analiza** cada oportunidad con un swarm de 5 agentes de IA, cada uno con una perspectiva distinta
3. **Calcula** el tamaño óptimo de posición usando Kelly Criterion (1/4 Kelly conservador)
4. **Ejecuta** la orden en Alpaca Markets (o simula en modo paper)
5. **Notifica** cada decisión por Telegram en tiempo real

---

## Arquitectura

```
pharma-bot/
├── bot.py               # Orquestador principal — loop y scheduler
├── pharma_scanner.py    # Detecta oportunidades (ClinicalTrials + FDA + precios)
├── alpaca_bridge.py     # Broker connector — órdenes, precios, posiciones
├── Multi_Person.py      # Swarm de 5 agentes IA (Claude Haiku)
├── kelly.py             # Position sizing con Kelly Criterion
├── Notifier.py          # Alertas por Telegram
├── data/
│   └── watchlist.py     # Lista de empresas monitoreadas
├── logs/
│   └── bot.log          # Registro de cada ciclo y trade
├── .env                 # API keys (nunca subir a GitHub)
└── requirements.txt     # Dependencias Python
```

---

## Los 5 agentes IA

Cada oportunidad es analizada por 5 perspectivas independientes. El consenso determina la señal final:

| Agente | Rol |
|---|---|
| `biotech_analyst` | Evalúa solidez científica del ensayo clínico |
| `fda_expert` | Estima probabilidad de aprobación regulatoria |
| `quant_trader` | Analiza momentum de precio y volumen |
| `risk_manager` | Identifica razones por las que puede fallar |
| `contrarian` | Argumenta por qué el mercado ya lo tiene priceado |

---

## Fuentes de datos

| Fuente | Datos | Costo |
|---|---|---|
| ClinicalTrials.gov API | Ensayos clínicos activos (Fase II/III) | Gratis |
| OpenFDA API | Historial de aprobaciones y rechazos | Gratis |
| Alpaca Markets | Precios y datos históricos NASDAQ | Gratis |

---

## Watchlist inicial

`ACAD` · `SAVA` · `AGEN` · `ARWR` · `RCUS` · `FATE` · `KALA` · `TNYA` · `CABA` · `RVNC`

---

## Instalación

**Requisitos:** Python 3.11+, Git

```bash
# 1. Clonar el repositorio
git clone https://github.com/deretoz/pharma-bot.git
cd pharma-bot

# 2. Crear entorno virtual
python -m venv .venv

# Windows
.venv\Scripts\activate.bat

# Mac/Linux
source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt --only-binary=:all: -i https://pypi.org/simple/

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys
```

---

## Configuración (.env)

```env
# Broker — Alpaca Markets
ALPACA_API_KEY=
ALPACA_SECRET_KEY=
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# IA — Anthropic Claude
ANTHROPIC_API_KEY=

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Config del bot
DRY_RUN=True           # True = paper trading, False = dinero real
MAX_POSITION_PCT=0.05  # Máximo 5% del capital por trade
STOP_LOSS_PCT=-0.15    # Stop loss automático en -15%
MIN_EDGE=0.05          # Edge mínimo para operar (5%)
```

### Cuentas necesarias

- **Alpaca Markets** — alpaca.markets (gratis, incluye paper trading)
- **Anthropic** — console.anthropic.com (mínimo $5 USD en créditos)
- **Telegram Bot** — @BotFather en Telegram (gratis)

---

## Uso

```bash
# Activar entorno virtual (Windows)
.venv\Scripts\activate.bat

# Correr el bot
python bot.py
```

El bot detecta automáticamente si el mercado está abierto. Si está cerrado, espera al próximo ciclo.

---

## Modo paper vs real

El bot opera en **modo paper por defecto** (`DRY_RUN=True`). En este modo analiza y notifica por Telegram pero no ejecuta órdenes reales.

Para pasar a trading real, cambiar en `.env`:

```env
ALPACA_BASE_URL=https://api.alpaca.markets
DRY_RUN=False
```

**Recomendación:** operar mínimo 30 trades en papel con win rate ≥ 55% antes de activar dinero real.

---

## Gestión de riesgo

- **Kelly Criterion** (1/4 Kelly) — limita cada trade al tamaño óptimo estadístico
- **Tope por trade** — nunca más del 5% del capital en una sola posición
- **Stop loss automático** — cierra posiciones que caigan más del 15%
- **Edge mínimo** — solo opera si el swarm detecta al menos 5% de ventaja

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.11+ |
| IA / LLM | Claude Haiku (Anthropic) |
| Broker | Alpaca Markets |
| Datos científicos | ClinicalTrials.gov · OpenFDA |
| Notificaciones | Telegram Bot API |
| Scheduler | schedule |
| Datos de mercado | alpaca-py |

---

## Roadmap

- [x] Scanner de oportunidades farmacéuticas
- [x] Swarm de 5 agentes IA
- [x] Kelly Criterion para position sizing
- [x] Ejecución automática via Alpaca
- [x] Alertas por Telegram
- [ ] Dashboard web con historial de trades
- [ ] Modelo ML (XGBoost) para predicción de precios
- [ ] NLP con BioBERT para análisis de publicaciones PubMed
- [ ] Expansión de watchlist automática

---

## Advertencia

Este bot es un proyecto experimental. Las señales generadas no constituyen asesoramiento financiero. Opera siempre con capital que puedas permitirte perder y valida el sistema en paper trading antes de usar dinero real.

---

*Proyecto desarrollado con el apoyo de Claude (Anthropic)*
