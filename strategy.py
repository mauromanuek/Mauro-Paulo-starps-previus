# strategy.py
import pandas as pd
import numpy as np
from datetime import datetime

class TradingStrategy:
    
    def __init__(self, buffer_size=100):
        self.history = pd.DataFrame(columns=['close', 'volume'])
        self.buffer_size = buffer_size

    def add_tick(self, price: float, volume: float = 0.0):
        """Adiciona um novo preço (tick) e volume ao histórico."""
        
        new_row = pd.DataFrame([{'close': price, 'volume': volume}])
        self.history = pd.concat([self.history, new_row], ignore_index=True)

        if len(self.history) > self.buffer_size:
            self.history = self.history.iloc[-self.buffer_size:]
            
        self.history.reset_index(drop=True, inplace=True)

    def calculate_indicators(self):
        """Calcula Indicadores Técnicos: RSI, MAs (EMA) e Volatilidade (Bandas de Bollinger)."""
        
        if len(self.history) < 20: 
            return {}

        # 1. Médias Móveis (EMA)
        self.history['EMA20'] = self.history['close'].ewm(span=20, adjust=False).mean()
        self.history['EMA50'] = self.history['close'].ewm(span=50, adjust=False).mean()

        # 2. RSI (Índice de Força Relativa)
        delta = self.history['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        rs = avg_gain / avg_loss
        self.history['RSI'] = 100 - (100 / (1 + rs))

        # 3. Volatilidade (Bandas de Bollinger - BB)
        self.history['MA20'] = self.history['close'].rolling(window=20).mean()
        self.history['STD20'] = self.history['close'].rolling(window=20).std()
        self.history['UpperBB'] = self.history['MA20'] + (self.history['STD20'] * 2)
        self.history['LowerBB'] = self.history['MA20'] - (self.history['STD20'] * 2)

    def generate_signal(self, symbol: str, tf: str):
        """Gera o sinal de trading baseado nas regras dos e-books."""
        self.calculate_indicators()
        
        if self.history.empty or pd.isna(self.history['EMA20'].iloc[-1]) or pd.isna(self.history['RSI'].iloc[-1]):
            return {"action": None, "probability": 0.50, "reason": "Aguardando mais dados históricos para análise (Buffer Vazio).", "explanation": "Não há dados suficientes (pelo menos 20 pontos) para calcular indicadores confiáveis.", "generated_at": datetime.utcnow().isoformat()}

        # Últimos dados
        last = self.history.iloc[-1]
        
        signal = "HOLD"
        prob = 0.50
        reason = "Aguardando setup de alta convicção."

        # Regras
        trend_up = last['EMA20'] > last['EMA50']
        trend_down = last['EMA20'] < last['EMA50']
        oversold = last['RSI'] < 30
        overbought = last['RSI'] > 70
        
        # 3. Confirmação Final (Lógica Central)
        if trend_up and oversold:
            # Tendência de alta E sobrevendido: Reversão/Pullback. Sinal de CALL.
            signal = "CALL"
            prob = 0.85 
            reason = "Cruzamento de EMAs confirma tendência de Alta e RSI indica Sobrevenda no curto prazo (Pullback)."
            
        elif trend_down and overbought:
            # Tendência de baixa E sobrecomprado: Reversão/Pullback. Sinal de PUT.
            signal = "PUT"
            prob = 0.85
            reason = "Cruzamento de EMAs confirma tendência de Baixa e RSI indica Sobrecompra no curto prazo (Pullback)."
        
        elif trend_up:
            signal = "HOLD"
            prob = 0.60
            reason = "Mercado em forte tendência de alta (EMA20>EMA50). Aguardando correção ou consolidação para CALL."
            
        elif trend_down:
            signal = "HOLD"
            prob = 0.60
            reason = "Mercado em forte tendência de baixa (EMA20<EMA50). Aguardando correção ou consolidação para PUT."

        # Retorna o resultado
        return {
            "symbol": symbol,
            "tf": tf,
            "action": signal,
            "probability": prob,
            "reason": reason,
            "explanation": f"O último preço ({last['close']:.4f}) foi analisado. RSI: {last['RSI']:.2f}. EMA20: {last['EMA20']:.4f}. EMA50: {last['EMA50']:.4f}.",
            "generated_at": datetime.utcnow().isoformat()
        }
