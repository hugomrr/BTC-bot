import MetaTrader5 as mt5
import logging

logger = logging.getLogger("MT5Manager")

class MT5TradeManager:
    def __init__(self, symbol="BTCUSD"):
        self.symbol = symbol
        if not mt5.initialize():
            logger.error(f"Fallo al iniciar MT5: {mt5.last_error()}")

    def execute_trade(self, side, lot_size=0.01, stop_loss_points=5000, take_profit_points=10000):
        """Ejecuta órdenes con SL y TP automáticos para proteger el capital."""
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            logger.error(f"Símbolo {self.symbol} no encontrado.")
            return None
    # --- ARREGLO DE VOLUMEN (Nivel Ingeniero) ---
        min_lot = symbol_info.volume_min
        if lot_size < min_lot:
            lot_size = min_lot
            logger.warning(f"Ajustando volumen al mínimo permitido: {lot_size}")
        # --------------------------------------------
        tick = mt5.symbol_info_tick(self.symbol)
        point = symbol_info.point 
        price = tick.ask if side == 'buy' else tick.bid
        
        if side == 'buy':
            sl = price - (stop_loss_points * point)
            tp = price + (take_profit_points * point)
            order_type = mt5.ORDER_TYPE_BUY
        else:
            sl = price + (stop_loss_points * point)
            tp = price - (take_profit_points * point)
            order_type = mt5.ORDER_TYPE_SELL

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": float(lot_size),
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "magic": 202603,
            "comment": "Bot Dios Protegido",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Error en MT5: {result.comment} (Code: {result.retcode})")
        else:
            logger.info(f"✅ ¡Orden enviada! Ticket: {result.order}")
        
        return result

    def get_account_summary(self):
        """Obtiene el estado actual de la cuenta en Axi."""
        account_info = mt5.account_info()
        if account_info is None:
            return "❌ No se pudo obtener la info de la cuenta."
        
        summary = (
            f"💰 **RESUMEN DE CUENTA**\n"
            f"---------------------------\n"
            f"• **Balance:** {account_info.balance:.2f} {account_info.currency}\n"
            f"• **Equidad:** {account_info.equity:.2f}\n"
            f"• **Margen Libre:** {account_info.margin_free:.2f}\n"
            f"• **Beneficio Actual:** {account_info.profit:.2f}"
        )
        return summary