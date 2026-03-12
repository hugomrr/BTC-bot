import asyncio
import MetaTrader5 as mt5
import logging
from mt5_manager import MT5TradeManager
from strategy_engine import StrategyEngine
from notifier import send_telegram_message, check_telegram_commands

# Configuración de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger("MainBotMT5")

async def start_trading_mt5():
    symbol = "BTCUSD" 
    manager = MT5TradeManager(symbol)
    strategy = StrategyEngine()
    
    # --- CAMBIO 1: El contador de mensajes leídos ---
    last_processed_id = 0 
    
    logger.info("Esperando conexión con el terminal MT5...")
    send_telegram_message("🚀 Bot Dios Online. Conectado a Axi (MT5). ¡Listo para el combate!")

    try:
        while True:
            # --- NUEVO: SEGURO DE FRANCOTIRADOR (Anti-Metralleta) ---
            posiciones = mt5.positions_get(symbol=symbol)
            if posiciones is not None and len(posiciones) > 0:
                logger.info(f"⏳ Sniper recargando: Operación en curso para {symbol}. Esperando cierre...")
                
                # Sigue escuchando Telegram por si le pides el /balance
                mensaje_usuario, update_id = check_telegram_commands() 
                if update_id and update_id > last_processed_id:
                    if mensaje_usuario == "/balance":
                        resumen = manager.get_account_summary()
                        send_telegram_message(resumen)
                    last_processed_id = update_id 
                
                await asyncio.sleep(10)
                continue
            # --------------------------------------------------------

            # 1. Datos
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 50)
            
            if rates is None or len(rates) < 20:
                logger.warning("Esperando a que MT5 entregue datos suficientes...")
                await asyncio.sleep(5)
                continue

            price_history = [rate['close'] for rate in rates]
            current_price = price_history[-1]

            # 2. Señal (Ajustado el mensaje de log para que sea más claro)
            signal = strategy.get_signal(price_history)
            logger.info(f"🔍 [SCAN] {symbol}: {current_price} | ESTRATEGIA: {signal}")

            # 3. Trading (Ajustado para ~2€ de Riesgo y ~4€ de Beneficio en BTC)
            if signal == "BUY":
                order = manager.execute_trade('buy', lot_size=0.01, stop_loss_points=2000, take_profit_points=4000)
                if order:
                    send_telegram_message(f"📈 COMPRA Sniper en Axi: {current_price} USDT")
            elif signal == "SELL":
                order = manager.execute_trade('sell', lot_size=0.01, stop_loss_points=2000, take_profit_points=4000)
                if order:
                    send_telegram_message(f"📉 VENTA Sniper en Axi: {current_price} USDT")

            # --- CAMBIO 2: SECCIÓN DE COMANDOS (Lógica de un solo uso) ---
            mensaje_usuario, update_id = check_telegram_commands() 
            
            if update_id and update_id > last_processed_id:
                if mensaje_usuario == "/balance":
                    logger.info(f"Comando /balance nuevo detectado (ID: {update_id})")
                    resumen = manager.get_account_summary()
                    send_telegram_message(resumen)
                
                # Guardamos el ID para no volver a procesarlo nunca más
                last_processed_id = update_id 

            # Escaneo cada 10 segundos
            await asyncio.sleep(10) 
            
    except Exception as e:
        logger.critical(f"Fallo en el bucle principal: {e}")
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    asyncio.run(start_trading_mt5())