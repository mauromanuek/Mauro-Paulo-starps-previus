# strategy.py - CÓDIGO ORIGINAL DO USUÁRIO (Lógica RSI/EMA)

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

# A lista para armazenar os ticks de preço (últimos 20 ticks)
ticks_history = []
MAX_TICKS = 20  # Mínimo de ticks para calcular os indicadores


def update_ticks(new_tick: float):
    """Adiciona um novo tick à história e mantém o tamanho em MAX_TICKS."""
    global ticks_history
    ticks_history.append(new_tick)
    # Garante que a lista não exceda o limite, mantendo apenas os mais recentes
    if len(ticks_history) > MAX_TICKS:
        ticks_history = ticks_history[-MAX_TICKS:]


def calculate_indicators() -> Dict[str, Any]:
    """
    Calcula o RSI e EMA usando os últimos ticks de preço.
    Retorna {} se não houver dados suficientes.
    """
    if len(ticks_history) < MAX_TICKS:
        return {} # Retorna dicionário vazio se não há dados suficientes

    # Converte a lista para uma Série Pandas para cálculo de indicadores
    prices = pd.Series(ticks_history)
    
    # 1. RSI (Relative Strength Index)
    # Período comum para RSI é 14, mas ajustamos para o nosso pequeno volume de ticks (MAX_TICKS)
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Cálculo da Média Móvel Exponencial (EMA) para RSI
    avg_gain = gain.ewm(com=MAX_TICKS - 1, min_periods=MAX_TICKS).mean().iloc[-1]
    avg_loss = loss.ewm(com=MAX_TICKS - 1, min_periods=MAX_TICKS).mean().iloc[-1]

    if avg_loss == 0:
        rs = 999.0 # Evita divisão por zero
    else:
        rs = avg_gain / avg_loss
    
    rsi = 100 - (100 / (1 + rs))
    
    # 2. EMA (Média Móvel Exponencial) - Período 10
    # Usamos um período menor, ajustado ao MAX_TICKS
    ema = prices.ewm(span=10, adjust=False).mean().iloc[-1]

    return {
        "rsi": rsi,
        "ema": ema,
        "last_price": prices.iloc[-1]
    }


def generate_signal(indicators: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Gera um sinal de trading (CALL/PUT) baseado nos indicadores."""
    
    if not indicators:
        return None
        
    rsi = indicators['rsi']
    ema = indicators['ema']
    price = indicators['last_price']
    
    action = None
    reason = f"RSI: {rsi:.2f}, Preço: {price:.4f}, EMA (10): {ema:.4f}"
    explanation = ("O RSI (Índice de Força Relativa) e a EMA (Média Móvel Exponencial) são usados para identificar extremos e a tendência.")
    
    # Regra da Estratégia: Extremos (Sobrecompra/Sobrevenda) alinhados com a tendência
    if rsi > 70 and price > ema:
        # RSI acima de 70 (sobrecompra) e preço acima da EMA (tendência de alta)
        action = "PUT (VENDA)"
        reason += ". RSI está em sobrecompra e o preço está acima da EMA. Espera-se uma correção."
        explanation += "Sinal de reversão de uma alta extrema."
        
    elif rsi < 30 and price < ema:
        # RSI abaixo de 30 (sobrevenda) e preço abaixo da EMA (tendência de baixa)
        action = "CALL (COMPRA)"
        reason += ". RSI está em sobrevenda e o preço está abaixo da EMA. Espera-se uma correção."
        explanation += "Sinal de reversão de uma baixa extrema."
        
    if action is None:
        return None 

    return {
        "action": action,
        "probability": 0.85, 
        "reason": reason,
        "explanation": explanation
    }
    
