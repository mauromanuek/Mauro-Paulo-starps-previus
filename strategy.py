import pandas as pd

class TradingStrategy:
    def __init__(self, short_period=9, long_period=21):
        self.short_period = short_period
        self.long_period = long_period

    def analyze(self, ticks):
        """
        Recebe uma lista de preços (ticks) e retorna 'BUY', 'SELL' ou 'NEUTRAL'.
        """
        if len(ticks) < self.long_period:
            return "Aguardando dados..."

        df = pd.DataFrame(ticks, columns=['price'])
        
        # Cálculo das EMAs
        df['ema_short'] = df['price'].ewm(span=self.short_period, adjust=False).mean()
        df['ema_long'] = df['price'].ewm(span=self.long_period, adjust=False).mean()

        last_short = df['ema_short'].iloc[-1]
        last_long = df['ema_long'].iloc[-1]
        prev_short = df['ema_short'].iloc[-2]
        prev_long = df['ema_long'].iloc[-2]

        # Lógica de Cruzamento
        if prev_short <= prev_long and last_short > last_long:
            return "BUY"
        elif prev_short >= prev_long and last_short < last_long:
            return "SELL"
        
        return "NEUTRAL"
