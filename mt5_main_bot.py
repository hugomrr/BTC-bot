"""
mt5_main_bot.py — Bucle principal del Sniper Bot (M1)

Máquina de estados:
  SCANNING   → Buscando señal. Escanea cada SCAN_INTERVAL_SECONDS.
  IN_TRADE   → Posición abierta. Solo monitorea, no abre nuevas.
  COOLDOWN   → Recién cerró una trade. Pausa obligatoria para evitar
               re-entradas emocionales en el mismo movimiento.
  ERROR      → Fallo puntual. Espera y vuelve a SCANNING.

Esta separación de estados es lo que convierte el bot en un sniper:
una bala bien colocada, recarga, disparo siguiente.
"""
import asyncio
import MetaTrader5 as mt5
import logging
import time
from enum import Enum, auto

import config
from mt5_manager import MT5TradeManager
from strategy_engine import StrategyEngine
from notifier import TelegramPoller, send_telegram_message

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("SniperBot")


# ── Máquina de estados ────────────────────────────────────────────────────────
class State(Enum):
    SCANNING = auto()
    IN_TRADE = auto()
    COOLDOWN = auto()
    ERROR    = auto()


# ── Comandos Telegram ─────────────────────────────────────────────────────────
def handle_telegram_commands(poller: TelegramPoller, manager: MT5TradeManager):
    """Procesa todos los comandos pendientes de Telegram en la cola."""
    while True:
        cmd = poller.get_next_command()
        if cmd is None:
            break
        logger.info(f"📩 Comando Telegram recibido: '{cmd}'")
        if cmd == "/balance":
            send_telegram_message(manager.get_account_summary())
        elif cmd == "/status":
            estado = "🟢 En posición" if manager.has_open_position() else "🔵 Escaneando"
            send_telegram_message(f"*Estado del bot:* {estado}")
        elif cmd == "/help":
            send_telegram_message(
                "📋 *Comandos disponibles:*\n"
                "/balance — Resumen de cuenta\n"
                "/status  — Estado actual del bot\n"
                "/help    — Esta ayuda"
            )
        else:
            send_telegram_message(f"❓ Comando desconocido: `{cmd}`\nUsa /help para ver opciones.")


# ── Bucle principal ───────────────────────────────────────────────────────────
async def run_sniper():
    # Asignar el timeframe M1 aquí (necesita que mt5 esté importado)
    config.TIMEFRAME = mt5.TIMEFRAME_M1

    manager  = MT5TradeManager(config.SYMBOL)
    strategy = StrategyEngine()
    poller   = TelegramPoller()

    state         = State.SCANNING
    cooldown_until = 0.0           # Timestamp hasta el que está en cooldown

    logger.info("🎯 Sniper Bot arrancado.")
    send_telegram_message(
        f"🎯 *Sniper Bot Online*\n"
        f"Símbolo: `{config.SYMBOL}` | TF: M1\n"
        f"SL: {config.STOP_LOSS_POINTS} pts | TP: {config.TAKE_PROFIT_POINTS} pts\n"
        f"Spread máx: {config.MAX_SPREAD_POINTS} pts\n"
        f"_Esperando señal de precisión..._"
    )

    while True:
        try:
            # ── Comandos Telegram (siempre, independientemente del estado) ──
            handle_telegram_commands(poller, manager)

            # ── Máquina de estados ──────────────────────────────────────────

            if state == State.COOLDOWN:
                remaining = cooldown_until - time.time()
                if remaining > 0:
                    logger.info(f"⏳ Cooldown: {remaining:.0f}s restantes...")
                    await asyncio.sleep(min(remaining, 5))
                    continue
                else:
                    logger.info("🔁 Cooldown terminado. Volviendo a escanear.")
                    state = State.SCANNING

            if state == State.IN_TRADE:
                if manager.has_open_position():
                    logger.info("📊 Posición activa. Monitoreando...")
                    await asyncio.sleep(config.POSITION_CHECK_SECONDS)
                    continue
                else:
                    # La posición se cerró (SL, TP o manual)
                    logger.info("✅ Posición cerrada. Entrando en cooldown.")
                    send_telegram_message(
                        f"🔄 Posición cerrada en `{config.SYMBOL}`.\n"
                        f"_Cooldown de {config.COOLDOWN_AFTER_TRADE}s antes del siguiente disparo._"
                    )
                    cooldown_until = time.time() + config.COOLDOWN_AFTER_TRADE
                    state = State.COOLDOWN
                    continue

            if state == State.ERROR:
                logger.warning("⚠️  Estado ERROR. Esperando antes de reintentar...")
                await asyncio.sleep(config.MT5_RECONNECT_WAIT_SECONDS)
                state = State.SCANNING
                continue

            # ── SCANNING ────────────────────────────────────────────────────
            # Verificar conexión MT5
            if not manager.ensure_connected():
                state = State.ERROR
                continue

            # Pedir velas M1
            rates = mt5.copy_rates_from_pos(
                config.SYMBOL, config.TIMEFRAME, 0, config.VELAS_HISTORIA
            )

            if rates is None or len(rates) < 50:
                logger.warning("Datos insuficientes de MT5. Reintentando...")
                await asyncio.sleep(5)
                continue

            prices = [r["close"] for r in rates]
            signal = strategy.get_signal(prices)
            action = signal.get("action", "HOLD")

            logger.info(
                f"🔍 {config.SYMBOL} M1 | "
                f"Precio: {signal.get('price', '?')} | "
                f"RSI: {signal.get('rsi', '?')} | "
                f"EMAf: {signal.get('ema_fast', '?')} | "
                f"EMAs: {signal.get('ema_slow', '?')} | "
                f"Señal: {action}"
            )

            if action in ("BUY", "SELL"):
                side  = "buy" if action == "BUY" else "sell"
                emoji = "📈" if action == "BUY" else "📉"

                result = manager.execute_trade(side)

                if result is not None:
                    send_telegram_message(
                        f"{emoji} *{action} ejecutado* en `{config.SYMBOL}`\n"
                        f"Precio: `{signal['price']}` | RSI: `{signal['rsi']}`\n"
                        f"SL: `{config.STOP_LOSS_POINTS} pts` | TP: `{config.TAKE_PROFIT_POINTS} pts`"
                    )
                    state = State.IN_TRADE
                else:
                    # La orden fue rechazada (spread, slippage, etc.)
                    # No cambiamos de estado, seguimos escaneando
                    logger.warning("Orden no ejecutada. Continuando escaneo.")

            await asyncio.sleep(config.SCAN_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            logger.info("🛑 Bot detenido manualmente.")
            send_telegram_message("🛑 *Sniper Bot detenido* manualmente.")
            break
        except Exception as e:
            logger.critical(f"💥 Excepción no controlada: {e}", exc_info=True)
            send_telegram_message(f"⚠️ *Error inesperado:*\n`{e}`\nReintentando en {config.MT5_RECONNECT_WAIT_SECONDS}s...")
            state = State.ERROR
            await asyncio.sleep(config.MT5_RECONNECT_WAIT_SECONDS)

    mt5.shutdown()
    logger.info("MT5 desconectado. Bot cerrado.")


if __name__ == "__main__":
    asyncio.run(run_sniper())
