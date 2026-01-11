import pandas as pd
import numpy as np

# Memória de dados para cálculos precisos
ticks_history = []

def update_ticks(price):
    global ticks_history
    ticks_history.append(price)
    # Mantemos 200 pontos para garantir médias móveis estáveis
    if len(ticks_history) > 200:
        ticks_history.pop(0)

def calculate_indicators(prices):
    df = pd.Series(prices)
    if len(df) < 20: return None
    
    # RSI (14 períodos)
    delta = df.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # Médias Móveis Exponenciais (9 e 21)
    ema_9 = df.ewm(span=9).mean()
    ema_21 = df.ewm(span=21).mean()
    
    return {
        "rsi": rsi.iloc[-1],
        "ema_9": ema_9.iloc[-1],
        "ema_21": ema_21.iloc[-1],
        "price": df.iloc[-1]
    }

def generate_signal():
    if len(ticks_history) < 30:
        return {"status": "waiting", "reason": "Coletando dados de mercado..."}
    
    ind = calculate_indicators(ticks_history)
    if not ind: return None

    action = "AGUARDAR"
    probability = 0.0
    reason = "Mercado sem confluência clara."

    # Lógica de confluência para CALL
    if ind["price"] > ind["ema_9"] > ind["ema_21"] and ind["rsi"] > 52:
        action = "CALL (COMPRA)"
        probability = 0.86
        reason = "Tendência de Alta + RSI em ascensão."
    
    # Lógica de confluência para PUT
    elif ind["price"] < ind["ema_9"] < ind["ema_21"] and ind["rsi"] < 48:
        action = "PUT (VENDA)"
        probability = 0.83
        reason = "Tendência de Baixa + RSI em queda."

    return {
        "action": action,
        "probability": probability,
        "reason": reason,
        "status": "active" if action != "AGUARDAR" else "waiting"
    }

def get_macro_analysis():
    """Análise de contexto para o Dashboard"""
    if len(ticks_history) < 50:
        return {"trend": "---", "volatility": "---"}
    
    prices = pd.Series(ticks_history)
    trend = "ALTA" if prices.iloc[-1] > prices.mean() else "BAIXA"
    vol = "ALTA" if prices.std() > (prices.mean() * 0.002) else "NORMAL"
    
    return {"trend": trend, "volatility": vol}
