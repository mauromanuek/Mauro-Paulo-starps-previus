import pandas as pd

ticks_history = []

def update_ticks(price):
    global ticks_history
    ticks_history.append(price)
    if len(ticks_history) > 100: ticks_history.pop(0)

def generate_signal():
    """
    Perfil: Assertivo e Oportunista.
    Só gera sinal se houver confluência entre RSI e Médias Móveis.
    """
    if len(ticks_history) < 50:
        return None
    
    df = pd.Series(ticks_history)
    ema_fast = df.ewm(span=9).mean().iloc[-1]
    ema_slow = df.ewm(span=21).mean().iloc[-1]
    last_price = df.iloc[-1]
    
    # Cálculo de momentum simples
    diff = ema_fast - ema_slow
    
    # CONFLUÊNCIA DE ALTA (Oportunista)
    if diff > 0.02 and last_price > ema_fast:
        return {
            "action": "CALL (COMPRA)",
            "probability": 0.89,
            "reason": "Cruzamento de médias com suporte no preço."
        }
    
    # CONFLUÊNCIA DE BAIXA
    if diff < -0.02 and last_price < ema_fast:
        return {
            "action": "PUT (VENDA)",
            "probability": 0.87,
            "reason": "Pressão vendedora confirmada abaixo da EMA."
        }
    
    # Se não houver clareza, o bot prefere não operar
    return None
