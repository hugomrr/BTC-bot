"""
mt5_manager.py — Gestión de órdenes y cuenta en MT5

Mejoras sobre la versión anterior:
  - Control de spread antes de entrar (evita entrar en mercados ilíquidos)
  - Control de slippage máximo (deviación)
  - Reconexión automática si MT5 se desconecta
  - Manejo explícito de None en symbol_info y symbol_info_tick
  - Logs detallados de cada rechazo para poder diagnosticar
"""
import time
import MetaTrader5 as mt5
import logging
import config
from datetime import datetime, timedelta
logger = logging.getLogger("MT5Manager")


class MT5TradeManager:

    def __init__(self, symbol: str = config.SYMBOL):
        self.symbol = symbol
        self._connect()

    # ── Conexión ─────────────────────────────────────────────────────────────

    def _connect(self) -> bool:
        """Inicializa MT5. Devuelve True si tuvo éxito."""
        if mt5.initialize():
            info = mt5.account_info()
            if info:
                logger.info(
                    f"✅ MT5 conectado | Cuenta: {info.login} | "
                    f"Broker: {info.company} | Balance: {info.balance:.2f} {info.currency}"
                )
            return True
        logger.error(f"❌ Fallo al iniciar MT5: {mt5.last_error()}")
        return False

    def ensure_connected(self) -> bool:
        """Comprueba la conexión y reintenta si es necesario."""
        if mt5.terminal_info() is not None:
            return True
        logger.warning("⚠️  MT5 desconectado. Intentando reconectar...")
        time.sleep(config.MT5_RECONNECT_WAIT_SECONDS)
        return self._connect()

    # ── Utilidades ───────────────────────────────────────────────────────────

    def _get_symbol_info(self):
        info = mt5.symbol_info(self.symbol)
        if info is None:
            logger.error(f"Símbolo {self.symbol} no encontrado en MT5.")
        return info

    def _get_tick(self):
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            logger.error(f"No se pudo obtener tick para {self.symbol}.")
        return tick

    def _spread_ok(self, symbol_info, tick) -> bool:
        """Devuelve False si el spread actual supera el máximo configurado."""
        spread_points = (tick.ask - tick.bid) / symbol_info.point
        if spread_points > config.MAX_SPREAD_POINTS:
            logger.warning(
                f"⛔ Spread demasiado alto: {spread_points:.0f} pts "
                f"(máx {config.MAX_SPREAD_POINTS}). Orden cancelada."
            )
            return False
        return True

    # ── Ejecución de órdenes ─────────────────────────────────────────────────

    def execute_trade(self, side: str) -> object | None:
        """
        Ejecuta una orden de mercado con SL, TP y control de slippage.

        Parámetros vienen de config.py para tener una única fuente de verdad.
        Devuelve el resultado de mt5.order_send() o None si hay algún problema
        previo al envío.
        """
        if not self.ensure_connected():
            return None

        symbol_info = self._get_symbol_info()
        if symbol_info is None:
            return None

        tick = self._get_tick()
        if tick is None:
            return None

        if not self._spread_ok(symbol_info, tick):
            return None

        # Ajuste de lote al mínimo permitido por el broker
        lot = max(config.LOT_SIZE, symbol_info.volume_min)
        point = symbol_info.point

        if side == "buy":
            price      = tick.ask
            sl         = price - config.STOP_LOSS_POINTS   * point
            tp         = price + config.TAKE_PROFIT_POINTS * point
            order_type = mt5.ORDER_TYPE_BUY
        else:
            price      = tick.bid
            sl         = price + config.STOP_LOSS_POINTS   * point
            tp         = price - config.TAKE_PROFIT_POINTS * point
            order_type = mt5.ORDER_TYPE_SELL

        request = {
            "action":      mt5.TRADE_ACTION_DEAL,
            "symbol":      self.symbol,
            "volume":      float(lot),
            "type":        order_type,
            "price":       price,
            "sl":          round(sl, symbol_info.digits),
            "tp":          round(tp, symbol_info.digits),
            "deviation":   config.MAX_SLIPPAGE_POINTS,  # Slippage máximo en puntos
            "magic":       202603,
            "comment":     "SniperBot v2",
            "type_time":   mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
          # Dentro del diccionario 'request' en execute_trade:
            "magic":       config.MAGIC_NUMBER,
            "comment":     config.BOT_NAME,
        }

        logger.info(
            f"📤 Enviando orden {side.upper()} | "
            f"Precio: {price} | SL: {sl:.2f} | TP: {tp:.2f} | Lote: {lot}"
        )

        result = mt5.order_send(request)

        if result is None:
            logger.error(f"mt5.order_send devolvió None. Error: {mt5.last_error()}")
            return None

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(
                f"❌ Orden rechazada | Código: {result.retcode} | "
                f"Motivo: {result.comment}"
            )
            return None

        logger.info(
            f"✅ Orden ejecutada | Ticket: {result.order} | "
            f"Precio real: {result.price}"
        )
        return result

    # ── Estado de cuenta ─────────────────────────────────────────────────────

    def get_account_summary(self) -> str:
        if not self.ensure_connected():
            return "❌ MT5 desconectado. No se pudo obtener el balance."

        info = mt5.account_info()
        if info is None:
            return "❌ No se pudo obtener la info de la cuenta."

        # Posiciones abiertas de ESTE bot
        posiciones = mt5.positions_get(symbol=self.symbol)
        pos_abiertas = [p for p in posiciones if p.magic == config.MAGIC_NUMBER] if posiciones else []
        pos_text = f"{len(pos_abiertas)} abierta(s)"

        # --- MAGIA QUANT: Calcular Beneficio Histórico de ESTE bot ---
        hoy = datetime.now()
        inicio_año = datetime(hoy.year, 1, 1) # Mira desde principio de año
        
        deals = mt5.history_deals_get(inicio_año, hoy + timedelta(days=1))
        beneficio_bot = 0.0
        trades_cerrados = 0

        if deals is not None:
            for deal in deals:
                # Si el DNI coincide y es una operación de salida (cierre con profit)
                if deal.magic == config.MAGIC_NUMBER and deal.symbol == self.symbol:
                    beneficio_bot += deal.profit
                    if deal.entry == mt5.DEAL_ENTRY_OUT: 
                        trades_cerrados += 1
        # -------------------------------------------------------------

        return (
            f"🤖 *{config.BOT_NAME}* | Símbolo: {self.symbol}\n"
            f"{'─' * 28}\n"
            f"💰 *Balance Global:* `{info.balance:.2f} {info.currency}`\n"
            f"📈 *P&L de ESTE bot:* `{beneficio_bot:+.2f} {info.currency}`\n"
            f"🎯 *Tiros cerrados:* `{trades_cerrados}`\n"
            f"🔫 *Balas en aire:* {pos_text}"
        )
    def has_open_position(self) -> bool:
        """Devuelve True si hay alguna posición abierta en el símbolo."""
        if not self.ensure_connected():
            return True  # Si no sé, asumo que hay posición (conservador)
        positions = mt5.positions_get(symbol=self.symbol)
        return positions is not None and len(positions) > 0
