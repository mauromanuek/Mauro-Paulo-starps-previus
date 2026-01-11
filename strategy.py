import pandas as pd

def calculate_signal(tick_history):
    if len(tick_history) < 14:
        return {"action": "WAIT", "prob": 0, "reason": "Aguardando dados..."}

    df = pd.DataFrame(tick_history, columns=['quote'])
    df['ema'] = df['quote'].ewm(span=14, adjust=False).mean()
    
    current_price = df['quote'].iloc[-1]
    current_ema = df['ema'].iloc[-1]
    
    if current_price > (current_ema + 0.05):
        return {"action": "CALL", "prob": 82, "reason": "Preço acima da EMA 14 (Tendência de Alta)"}
    elif current_price < (current_ema - 0.05):
        return {"action": "PUT", "prob": 85, "reason": "Preço abaixo da EMA 14 (Tendência de Baixa)"}
    
    return {"action": "NEUTRAL", "prob": 0, "reason": "Preço em zona de consolidação"}
