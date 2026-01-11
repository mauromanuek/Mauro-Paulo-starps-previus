import pandas as pd
import numpy as np

ticks_history = []

def update_ticks(price):
    global ticks_history
    ticks_history.append(price)
    if len(ticks_history) > 200:
        ticks_history.pop(0)

def generate_signal():
    if len(ticks_history) < 20:
        return {"status": "waiting"}
    
    df = pd.Series(ticks_history)
    ema = df.ewm(span=14).mean().iloc[-1]
    last_price = df.iloc[-1]
    
    action = "AGUARDAR"
    prob = 0.50
    if last_price > ema:
        action = "CALL (COMPRA)"
        prob = 0.82
    elif last_price < ema:
        action = "PUT (VENDA)"
        prob = 0.79

    return {
        "status": "active",
        "action": action,
        "probability": prob,
        "reason": "Tendência baseada em cruzamento de média"
    }
