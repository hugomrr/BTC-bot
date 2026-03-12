"""
strategy_engine.py — Motor de señales Sniper (M1)

Estrategia: Bollinger Bands + RSI + Filtro de Tendencia (EMA9/EMA21)

Lógica de entrada:
  BUY  → precio toca/cruza banda inferior BB  AND  RSI < RSI_OVERSOLD
          AND  EMA_fast > EMA_slow  (tendencia alcista o lateral-alcista)

  SELL → precio toca/cruza banda superior BB  AND  RSI > RSI_OVERBOUGHT
          AND  EMA_fast < EMA_slow  (tendencia bajista o lateral-bajista)

El filtro EMA evita entrar contratendencia en impulsos fuertes,
que es la causa principal de pérdidas con BB+RSI puros en M1.
"""
import numpy as np
import logging
import config

logger = logging.getLogger("StrategyEngine")


class StrategyEngine:
    def __init__(self):
        self.rsi_period     = config.RSI_PERIOD
        self.rsi_oversold   = config.RSI_OVERSOLD
        self.rsi_overbought = config.RSI_OVERBOUGHT
        self.bb_period      = config.BB_PERIOD
        self.bb_std         = config.BB_STD
        self.ema_fast       = config.EMA_FAST
        self.ema_slow       = config.EMA_SLOW

    # ── Indicadores ──────────────────────────────────────────────────────────

    def _ema(self, prices: np.ndarray, period: int) -> float:
        """EMA del último valor usando la fórmula estándar de suavizado."""
        if len(prices) < period:
            return float(np.mean(prices))
        k = 2.0 / (period + 1)
        ema = float(np.mean(prices[:period]))
        for price in prices[period:]:
            ema = price * k + ema * (1 - k)
        return ema

    def _rsi(self, prices: np.ndarray) -> float:
        """
        RSI con suavizado de Wilder (EMA de ganancias/pérdidas).
        Protegido contra división por cero:
          - down == 0  →  mercado en subida pura → RSI = 100
          - up   == 0  →  mercado en bajada pura → RSI = 0
        """
        if len(prices) < self.rsi_period + 1:
            return 50.0  # Valor neutro mientras hay pocas velas

        deltas = np.diff(prices.astype(float))
        gains  = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        # Seed inicial: media simple del primer período
        avg_gain = float(np.mean(gains[:self.rsi_period]))
        avg_loss = float(np.mean(losses[:self.rsi_period]))

        # Suavizado de Wilder para el resto de velas
        for i in range(self.rsi_period, len(gains)):
            avg_gain = (avg_gain * (self.rsi_period - 1) + gains[i])  / self.rsi_period
            avg_loss = (avg_loss * (self.rsi_period - 1) + losses[i]) / self.rsi_period

        if avg_loss == 0:
            return 100.0
        if avg_gain == 0:
            return 0.0

        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _bollinger(self, prices: np.ndarray) -> tuple[float, float, float]:
        """Devuelve (upper, sma, lower) de las últimas bb_period velas."""
        window = prices[-self.bb_period:]
        sma    = float(np.mean(window))
        std    = float(np.std(window, ddof=0))
        return sma + self.bb_std * std, sma, sma - self.bb_std * std

    # ── Señal principal ──────────────────────────────────────────────────────

    def get_signal(self, prices: list[float]) -> dict:
        """
        Analiza los precios de cierre y devuelve un dict con:
          {
            "action":      "BUY" | "SELL" | "HOLD" | "WAIT",
            "rsi":         float,
            "upper_band":  float,
            "lower_band":  float,
            "ema_fast":    float,
            "ema_slow":    float,
            "price":       float,
          }
        Devolver el dict en lugar de solo el string permite que el main
        loguee detalles sin recalcular nada.
        """
        arr = np.array(prices, dtype=float)

        min_bars = max(self.bb_period, self.rsi_period + 1, self.ema_slow + 1)
        if len(arr) < min_bars:
            return {"action": "WAIT"}

        upper, sma, lower = self._bollinger(arr)
        rsi       = self._rsi(arr)
        ema_f     = self._ema(arr, self.ema_fast)
        ema_s     = self._ema(arr, self.ema_slow)
        price     = float(arr[-1])

        result = {
            "action":     "HOLD",
            "rsi":        round(rsi, 2),
            "upper_band": round(upper, 2),
            "lower_band": round(lower, 2),
            "ema_fast":   round(ema_f, 2),
            "ema_slow":   round(ema_s, 2),
            "price":      round(price, 2),
        }

        # ── Condición BUY ────────────────────────────────────────────────────
        # Precio toca o perfora la banda inferior  +  RSI sobrevendido
        # +  tendencia no es bajista fuerte (ema_fast >= ema_slow)
        if price <= lower and rsi < self.rsi_oversold and ema_f >= ema_s:
            result["action"] = "BUY"

        # ── Condición SELL ───────────────────────────────────────────────────
        # Precio toca o perfora la banda superior  +  RSI sobrecomprado
        # +  tendencia no es alcista fuerte (ema_fast <= ema_slow)
        elif price >= upper and rsi > self.rsi_overbought and ema_f <= ema_s:
            result["action"] = "SELL"

        return result
