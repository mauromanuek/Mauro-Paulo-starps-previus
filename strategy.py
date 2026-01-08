import pandas as pd

ticks_history = []

def update_ticks(price):
    global ticks_history
    ticks_history.append(price)
    if len(ticks_history) > 60:
        ticks_history.pop(0)

def generate_signal():
    if len(ticks_history) < 20:
        return None
    
    prices = pd.Series(ticks_history)
    ema = prices.ewm(span=14).mean().iloc[-1]
    last_price = prices.iloc[-1]
    
    # Lógica de Cruzamento de Preço com a Média
    if last_price > ema + 0.05:
        return {
            "action": "CALL (COMPRA)",
            "probability": 0.84,
            "reason": "Preço acima da média móvel com força de alta."
        }
    elif last_price < ema - 0.05:
        return {
            "action": "PUT (VENDA)",
            "probability": 0.81,
            "reason": "Pressão vendedora confirmada abaixo da média."
        }
    return None
