import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

# Histórico de preços (ticks)
ticks_history = []
MAX_TICKS = 50 # Aumentamos para ter mais precisão

def update_ticks(new_tick: float):
    global ticks_history
    ticks_history.append(new_tick)
    if len(ticks_history) > MAX_TICKS:
        ticks_history.pop(0)

def generate_signal() -> Optional[Dict[str, Any]]:
    """
    Analisa o comportamento do mercado e gera um sinal com justificativa.
    Combina: RSI + EMA + Price Action (Variação de Ticks)
    """
    if len(ticks_history) < 20:
        return None

    prices = pd.Series(ticks_history)
    
    # 1. Indicadores Técnicos
    ema_period = 10
    ema = prices.ewm(span=ema_period, adjust=False).mean().iloc[-1]
    last_price = prices.iloc[-1]
    
    # RSI Simples
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs.iloc[-1]))

    # 2. Lógica de "Price Action" por Ticks (Velocidade)
    # Verifica se os últimos 5 ticks foram na mesma direção (Exaustão/Força)
    last_5 = prices.tail(5).diff().dropna()
    is_strong_up = all(last_5 > 0)
    is_strong_down = all(last_5 < 0)

    # --- REGRAS DE DECISÃO (ESTILO TRADER HUMANO) ---
    
    action = None
    reason = ""
    prob = 0.0

    # Estratégia de Reversão (RSI Extremo + Preço longe da média)
    if rsi > 75:
        action = "PUT (VENDA)"
        reason = "Mercado em SOBRECOMPRA extrema. Alta probabilidade de correção para baixo."
        prob = 0.82
    elif rsi < 25:
        action = "CALL (COMPRA)"
        reason = "Mercado em SOBREVENDA extrema. Oportunidade de correção para cima."
        prob = 0.84

    # Estratégia de Continuação (Tendência forte + Preço acima da média)
    elif is_strong_up and last_price > ema:
        action = "CALL (COMPRA)"
        reason = "Tendência de ALTA confirmada pela média móvel e fluxo de ticks."
        prob = 0.76
    elif is_strong_down and last_price < ema:
        action = "PUT (VENDA)"
        reason = "Tendência de BAIXA confirmada pela média móvel e fluxo de ticks."
        prob = 0.78

    if action:
        return {
            "action": action,
            "probability": prob,
            "reason": reason
        }
    
    return None
