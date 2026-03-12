"""
config.py — Configuración central del Sniper Bot
NUNCA pongas credenciales aquí. Usa un archivo .env en la raíz del proyecto.

Archivo .env (crea este archivo y añádelo a .gitignore):
------------------------------------------------------------
TELEGRAM_TOKEN=tu_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui
------------------------------------------------------------
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ── Símbolo y timeframe ───────────────────────────────────────────────────────
SYMBOL          = "BTCUSD"
TIMEFRAME       = None          # Se asigna en runtime como mt5.TIMEFRAME_M1
VELAS_HISTORIA  = 100           # Velas que se piden a MT5 (M1 → últimas 100 min)

# ── Gestión de riesgo ─────────────────────────────────────────────────────────
LOT_SIZE            = 0.01      # Lote mínimo
STOP_LOSS_POINTS    = 1500      # ~15 USD en BTC con point≈0.01
TAKE_PROFIT_POINTS  = 3000      # RR 1:2
MAX_SLIPPAGE_POINTS = 300       # Slippage máximo tolerado antes de cancelar
MAX_SPREAD_POINTS   = 500       # Si el spread supera esto, no entramos

# ── Parámetros de la estrategia ───────────────────────────────────────────────
RSI_PERIOD     = 14
RSI_OVERSOLD   = 35             # Más permisivo que 30 para M1
RSI_OVERBOUGHT = 65             # Más permisivo que 70 para M1
BB_PERIOD      = 20
BB_STD         = 2.0
EMA_FAST       = 9              # EMA rápida para filtro de tendencia
EMA_SLOW       = 21             # EMA lenta para filtro de tendencia

# ── Tiempos del bucle ─────────────────────────────────────────────────────────
SCAN_INTERVAL_SECONDS      = 15   # Cada cuánto escanea cuando no hay posición
POSITION_CHECK_SECONDS     = 5    # Cada cuánto comprueba si sigue la posición abierta
COOLDOWN_AFTER_TRADE       = 60   # Segundos de pausa obligatoria tras cerrar una trade
MT5_RECONNECT_WAIT_SECONDS = 30   # Espera antes de reintentar conectar MT5

# ── Telegram polling ──────────────────────────────────────────────────────────
TELEGRAM_TIMEOUT = 5            # Timeout en segundos para requests de Telegram
