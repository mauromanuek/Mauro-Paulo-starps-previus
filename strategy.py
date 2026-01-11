import pandas as pd
import numpy as np

# Memória expandida para análise de velas e ticks
ticks_history = []
candles_history = []

def update_ticks(price):
    global ticks_history
    ticks_history.append(price)
    # Mantemos 200 pontos para cálculos de médias longas (EMA 200) e volatilidade
    if len(ticks_history) > 200:
        ticks_history.pop(0)

def calculate_indicators(prices):
    df = pd.Series(prices)
    
    # RSI (Relative Strength Index)
    delta = df.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # Bandas de Bollinger (20 períodos, 2 desvios)
    sma_20 = df.rolling(window=20).mean()
    std_20 = df.rolling(window=20).std()
    upper_band = sma_20 + (std_20 * 2)
    lower_band = sma_20 - (std_20 * 2)
    
    # Médias Móveis Exponenciais
    ema_9 = df.ewm(span=9).mean()
    ema_21 = df.ewm(span=21).mean()
    
    return {
        "rsi": rsi.iloc[-1],
        "upper": upper_band.iloc[-1],
        "lower": lower_band.iloc[-1],
        "ema_9": ema_9.iloc[-1],
        "ema_21": ema_21.iloc[-1],
        "last_price": df.iloc[-1],
        "prev_price": df.iloc[-2] if len(df) > 1 else df.iloc[-1]
    }

def generate_signal():
    """Gera sinais com base em confluência técnica de alta probabilidade"""
    if len(ticks_history) < 30:
        return None
    
    ind = calculate_indicators(ticks_history)
    prob = 0.50
    reasons = []
    scenario = "Indefinição"
    
    # Análise de Estrutura
    if ind["last_price"] > ind["ema_9"] > ind["ema_21"]:
        prob += 0.15
        reasons.append("Estrutura de Alta")
        scenario = "Continuação"
    elif ind["last_price"] < ind["ema_9"] < ind["ema_21"]:
        prob += 0.15
        reasons.append("Estrutura de Baixa")
        scenario = "Continuação"

    # Confluência RSI e Bollinger
    if ind["rsi"] < 30 and ind["last_price"] <= ind["lower"]:
        prob += 0.25
        action = "CALL (COMPRA)"
        reasons.append("Exaustão Vendedora")
        scenario = "Reversão"
    elif ind["rsi"] > 70 and ind["last_price"] >= ind["upper"]:
        prob += 0.25
        action = "PUT (VENDA)"
        reasons.append("Exaustão Compradora")
        scenario = "Reversão"
    else:
        action = "CALL (COMPRA)" if ind["last_price"] > ind["ema_9"] else "PUT (VENDA)"

    if prob < 0.75:
        return {
            "action": "AGUARDAR",
            "probability": prob,
            "reason": "Buscando confluência...",
            "scenario": "Lateralização",
            "status": "waiting"
        }

    return {
        "action": action,
        "probability": round(prob, 2),
        "reason": " + ".join(reasons),
        "scenario": scenario,
        "duration": "1-2 min",
        "status": "active"
    }

def get_macro_analysis():
    if len(ticks_history) < 50:
        return {"status": "loading", "trend": "Analizando...", "volatility": "---", "context": "Coletando Dados..."}
    
    df = pd.Series(ticks_history)
    ema_200 = df.ewm(span=200).mean().iloc[-1] if len(df) >= 200 else df.mean()
    current = df.iloc[-1]
    std_dev = df.std()
    
    trend = "ALTA" if current > ema_200 else "BAIXA"
    vol = "ALTA" if std_dev > (df.mean() * 0.0015) else "NORMAL"
    context = "Tendência" if abs(current - ema_200) > std_dev else "Consolidação"

    return {
        "status": "ready",
        "trend": trend,
        "volatility": vol,
        "context": context
    }
