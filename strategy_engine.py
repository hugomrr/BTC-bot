"""
strategy_engine.py — Motor MACD (Surfero de Tendencias)

Lógica de entrada (Tendencial):
  BUY  → La línea MACD cruza por encima de la línea Señal (Impulso alcista)
  SELL → La línea MACD cruza por debajo de la línea Señal (Impulso bajista)
"""
import numpy as np
import logging

logger = logging.getLogger("StrategyEngine_MACD")

class StrategyEngine:
    def __init__(self):
        # Parámetros clásicos del MACD
        self.fast_ema = 12
        self.slow_ema = 26
        self.signal_ema = 9

    def _ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calcula una serie de EMA para todo el array de precios."""
        ema = np.zeros_like(prices)
        if len(prices) < period:
            return ema
            
        ema[period-1] = np.mean(prices[:period])
        k = 2.0 / (period + 1)
        for i in range(period, len(prices)):
            ema[i] = prices[i] * k + ema[i-1] * (1 - k)
        return ema

    def get_signal(self, prices: list[float]) -> dict:
        arr = np.array(prices, dtype=float)

        if len(arr) < 50: # Necesitamos histórico para calcular el MACD bien
            return {"action": "WAIT"}

        # 1. Calculamos las EMAs base
        ema12 = self._ema(arr, self.fast_ema)
        ema26 = self._ema(arr, self.slow_ema)

        # 2. La línea MACD es la diferencia entre ambas
        macd_line = ema12 - ema26

        # 3. La línea de Señal es una EMA de la línea MACD
        signal_line = self._ema(macd_line, self.signal_ema)

        # Precios y valores actuales y anteriores (para ver el cruce)
        price_actual = round(float(arr[-1]), 2)
        macd_actual = macd_line[-1]
        signal_actual = signal_line[-1]
        
        macd_anterior = macd_line[-2]
        signal_anterior = signal_line[-2]

        result = {
            "action":     "HOLD",
            "price":      price_actual,
            "rsi":        "N/A", # Lo quitamos para no liar los logs,
            "ema_fast":   round(macd_actual, 2), # Usamos estos campos para loguear el MACD
            "ema_slow":   round(signal_actual, 2)
        }

        # ── Condición BUY (Cruce Alcista) ────────────────────────────────────
        # El MACD anterior estaba por debajo de la señal, y el actual está por encima
        if macd_anterior < signal_anterior and macd_actual > signal_actual:
            result["action"] = "BUY"

        # ── Condición SELL (Cruce Bajista) ───────────────────────────────────
        # El MACD anterior estaba por encima de la señal, y el actual está por debajo
        elif macd_anterior > signal_anterior and macd_actual < signal_actual:
            result["action"] = "SELL"

        return result
