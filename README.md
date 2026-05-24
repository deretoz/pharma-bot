# 🤖 Pharma Bot

Bot de trading automatizado especializado en acciones farmacéuticas y biotecnológicas del NASDAQ. Combina un swarm de 5 agentes de IA con distribuciones de probabilidad matemáticas y un agente de Reinforcement Learning entrenado con datos históricos reales.

---

## ¿Cómo funciona?

El bot corre un ciclo cada 30 minutos durante el horario de mercado (9:30am–4:00pm ET). En cada ciclo:

1. **Escanea** la watchlist buscando catalizadores científicos activos (ensayos Fase II/III, historial FDA, volumen inusual)
2. **Analiza** cada oportunidad con un swarm de 5 agentes IA — cada uno genera una distribución de probabilidad matemática independiente
3. **Agrega** las distribuciones ponderadas por confianza para obtener `p_success`, `p_failure` y `p_neutral`
4. **Valida** la señal con el agente de Reinforcement Learning (PPO) entrenado con 2 años de datos históricos
5. **Opera** solo cuando swarm y RL están de acuerdo — double validation
6. **Calcula** el tamaño óptimo de posición con Kelly Criterion usando las probabilidades reales
7. **Notifica** cada decisión por Telegram en tiempo real

---

## Arquitectura

```
pharma-bot/
├── bot.py                  # Orquestador principal — loop y scheduler
├── pharma_scanner.py       # Detecta oportunidades (ClinicalTrials + FDA + precios)
├── alpaca_bridge.py        # Broker connector — órdenes, precios, posiciones
├── Multi_Person.py         # Swarm v2 — 5 agentes con distribuciones de probabilidad
├── kelly.py                # Kelly Criterion v2 con probabilidades matemáticas
├── Notifier.py             # Alertas por Telegram
├── rl_environment.py       # Entorno Gymnasium para entrenamiento RL
├── rl_data_builder.py      # Pipeline de datos históricos + trades reales
├── rl_agent.py             # Entrenamiento del agente PPO
├── rl_bridge.py            # Puente RL ↔ Swarm — consenso en tiempo real
├── backtest.py             # Backtesting histórico del sistema
├── data/
│   └── rl_dataset.csv      # Dataset histórico (2,148 filas, 5 empresas, 2 años)
├── models/
│   └── pharma_ppo.zip      # Agente PPO entrenado
├── logs/
│   ├── bot.log             # Registro de cada ciclo
│   └── trades.csv          # Historial de señales generadas
├── .env                    # API keys (nunca subir a GitHub)
└── requirements.txt        # Dependencias Python
```

---

## Flujo completo de decisión

```
Scanner detecta catalizador científico
              ↓
    Swarm v2 — 5 agentes IA
    Cada agente genera:
    { p_success, p_failure, p_neutral, confidence }
              ↓
    Agregador ponderado por confianza
    → p_success / p_failure / edge final
              ↓
    Agente RL (PPO) analiza el estado
    → acción independiente del mercado
              ↓
         RL Bridge
    ┌─────────────────────┐
    │ ¿Swarm == RL?       │
    │ Sí → edge +25%      │
    │ No → MANTENER       │
    └─────────────────────┘
              ↓
    Kelly v2 calcula monto óptimo
    usando p_success y p_failure reales
              ↓
    Orden ejecutada en Alpaca
              ↓
    Notificación Telegram
```

---

## Los 5 agentes IA — Swarm v2

Cada agente genera una distribución de probabilidad matemática estricta basada en su especialidad:

| Agente | Especialidad | Base de estimación |
|---|---|---|
| `biotech_analyst` | Solidez científica del ensayo | Tasas históricas por fase (Fase III: 58% base) |
| `fda_expert` | Probabilidad regulatoria | Precedentes FDA, historial de aprobaciones/CRL |
| `quant_trader` | Movimiento de precio | Volumen relativo, momentum 30d, capitalización |
| `risk_manager` | Vectores de riesgo | Dilución, competidores, tipo de endpoint |
| `contrarian` | Precio ya priceado | Movimiento previo, volumen pre-evento |

El agregador combina las 5 distribuciones ponderadas por `confidence` — los agentes más seguros pesan más en la decisión final.

---

## Agente de Reinforcement Learning

| Parámetro | Valor |
|---|---|
| Algoritmo | PPO (Proximal Policy Optimization) |
| Dataset de entrenamiento | 2,148 días (5 empresas, 2 años) |
| Trades reales integrados | 90 trades del bot en paper trading |
| Timesteps de entrenamiento | 50,000 |
| State Space | 8 variables (precio, volumen, p_success, p_failure, posición, PnL) |
| Action Space | 3 acciones (COMPRAR, MANTENER, VENDER) |

**Resultados en datos de test:**

| Estrategia | Retorno |
|---|---|
| Buy & Hold promedio | -15.6% |
| Agente RL | **+62.2%** |
| Ventaja sobre mercado | **+77.8%** |

---

## Fuentes de datos

| Fuente | Datos | Costo |
|---|---|---|
| ClinicalTrials.gov API | Ensayos clínicos activos (Fase II/III) | Gratis |
| OpenFDA API | Historial de aprobaciones y rechazos | Gratis |
| Alpaca Markets | Precios y datos históricos NASDAQ | Gratis |

---

## Watchlist

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

# Config del bot
DRY_RUN=True           # True = paper trading, False = dinero real
MAX_POSITION_PCT=0.05  # Máximo 5% del capital por trade
STOP_LOSS_PCT=-0.15    # Stop loss automático en -15%
MIN_EDGE=0.05          # Edge mínimo para operar (5%)

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
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

# Actualizar dataset y re-entrenar agente RL
python rl_data_builder.py
python rl_agent.py

# Correr backtest histórico
python backtest.py
```

---

## Modo paper vs real

El bot opera en **modo paper por defecto** (`DRY_RUN=True`). Para pasar a trading real:

```env
ALPACA_BASE_URL=https://api.alpaca.markets
DRY_RUN=False
```

**Checklist antes de operar con dinero real:**
- ✅ 30+ trades en papel completados
- ✅ Win rate ≥ 55% confirmado
- ✅ Drawdown máximo < 25%
- ✅ Stop losses probados y funcionando
- ✅ Agente RL re-entrenado con datos reales del bot

---

## Gestión de riesgo

- **Double validation** — opera solo cuando swarm IA y agente RL coinciden
- **Kelly Criterion v2** — usa `p_success` y `p_failure` reales para el tamaño óptimo
- **Tope por trade** — nunca más del 5% del capital en una sola posición
- **Stop loss automático** — cierra posiciones que caigan más del 15%
- **Edge mínimo** — solo opera si el sistema detecta al menos 5% de ventaja

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.11+ |
| IA / LLM | Claude Haiku (Anthropic) |
| Reinforcement Learning | Stable-Baselines3 PPO |
| Entorno RL | Gymnasium |
| Deep Learning | PyTorch |
| Broker | Alpaca Markets |
| Datos científicos | ClinicalTrials.gov · OpenFDA |
| Notificaciones | Telegram Bot API |
| Scheduler | schedule |

---

## Resultados actuales (paper trading)

| Métrica | Valor |
|---|---|
| Días operando | 5 |
| Total señales generadas | 90 |
| Empresas activas | ACAD, ARWR, RCUS |
| Edge promedio del swarm | ~10.5% |
| Backtest 12 meses | +418% retorno |
| Agente RL vs Buy&Hold | +77.8% ventaja |

---

## Roadmap

- [x] Scanner de oportunidades farmacéuticas
- [x] Swarm v2 — distribuciones de probabilidad matemáticas
- [x] Kelly Criterion v2 con probabilidades reales
- [x] Agente RL (PPO) entrenado con datos históricos
- [x] Double validation — consenso swarm + RL
- [x] Alertas por Telegram
- [x] Backtesting histórico
- [ ] Re-entrenamiento automático del agente RL cada semana
- [ ] Dashboard web con historial de trades
- [ ] NLP con BioBERT para análisis de publicaciones PubMed
- [ ] Expansión de watchlist automática
- [ ] Módulo de opciones financieras (calls pre-FDA)

---

## Advertencia

Este bot es un proyecto experimental. Las señales generadas no constituyen asesoramiento financiero. Opera siempre con capital que puedas permitirte perder y valida el sistema en paper trading antes de usar dinero real.

---

*Proyecto desarrollado con el apoyo de Claude (Anthropic)*