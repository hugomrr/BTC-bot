import numpy as np
import logging

logger = logging.getLogger("StrategyEngine")

class StrategyEngine:
    def __init__(self, rsi_period=14, bb_period=20, bb_std=2):
        self.rsi_period = rsi_period
        self.bb_period = bb_period
        self.bb_std = bb_std

    def calculate_rsi(self, prices):
        """Cálculo de RSI nivel institucional usando vectores de numpy."""
        if len(prices) < self.rsi_period: return 50
        deltas = np.diff(prices)
        seed = deltas[:self.rsi_period+1]
        up = seed[seed >= 0].sum()/self.rsi_period
        down = -seed[seed < 0].sum()/self.rsi_period
        rs = up/down
        rsi = np.zeros_like(prices)
        rsi[:self.rsi_period] = 100. - 100./(1. + rs)

        for i in range(self.rsi_period, len(prices)):
            delta = deltas[i - 1]
            if delta > 0:
                up_val, down_val = delta, 0.
            else:
                up_val, down_val = 0., -delta
            up = (up * (self.rsi_period - 1) + up_val) / self.rsi_period
            down = (down * (self.rsi_period - 1) + down_val) / self.rsi_period
            rs = up / down
            rsi[i] = 100. - 100. / (1. + rs)
        return rsi[-1]

    def get_signal(self, prices):
        """Decide la acción basada en Bollinger y RSI."""
        if len(prices) < self.bb_period:
            return "WAIT"
        
        # Cálculo de Bandas de Bollinger
        sma = np.mean(prices[-self.bb_period:])
        std = np.std(prices[-self.bb_period:])
        upper_band = sma + (self.bb_std * std)
        lower_band = sma - (self.bb_std * std)
        
        current_price = prices[-1]
        rsi = self.calculate_rsi(prices)

        # Lógica de decisión
        if current_price < lower_band and rsi < 30:
            return "BUY"
        elif current_price > upper_band and rsi > 70:
            return "SELL"
        
        return "HOLD"