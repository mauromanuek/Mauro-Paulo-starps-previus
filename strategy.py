# strategy.py

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List

# A lista para armazenar os ticks de preço (últimos 50 ticks para mais dados)
ticks_history: List[float] = []
MAX_TICKS = 50  # Mínimo de ticks para calcular os indicadores

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
    Retorna dicionário vazio se não houver dados suficientes.
    """
    global ticks_history
    # O RSI requer pelo menos 14 períodos para um cálculo preciso, mas usamos MAX_TICKS
    if len(ticks_history) < 15: 
        return {} 

    # Converte a lista para uma Série Pandas para cálculo de indicadores
    prices = pd.Series(ticks_history)
    
    # 1. RSI (Relative Strength Index) - Período de 14 como padrão da indústria
    RSI_PERIOD = 14
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Usa a média móvel exponencial (EMA) para suavizar
    avg_gain = gain.ewm(span=RSI_PERIOD, adjust=False).mean()
    avg_loss = loss.ewm(span=RSI_PERIOD, adjust=False).mean()
    
    # Previne divisão por zero
    rs = avg_gain / avg_loss.replace(0, 1e-10) 
    
    # Apenas o último RSI calculado é o de interesse
    rsi_value = 100.0 - (100.0 / (1.0 + rs)).iloc[-1] 
    
    # 2. EMA (Exponential Moving Average) - Período de 10
    EMA_PERIOD = 10
    ema_value = prices.ewm(span=EMA_PERIOD, adjust=False).mean().iloc[-1]
    
    return {
        "rsi": rsi_value,
        "ema": ema_value,
        "last_price": prices.iloc[-1]
    }

def generate_signal(indicators: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Gera um sinal de trading (CALL/PUT) baseado em RSI e EMA.
    (Sua estratégia original baseada em extremos do RSI)
    """
    if not indicators or not indicators.get('rsi'):
        return None
        
    rsi = indicators['rsi']
    ema = indicators['ema']
    price = indicators['last_price']
    
    action = None
    probability = 0.0
    reason = f"RSI: {rsi:.2f}, Preço: {price:.4f}, EMA (10): {ema:.4f}"
    explanation = "O RSI mede a velocidade do preço. EMAs mostram a tendência."
    
    # Regra da Estratégia (Extremos)
    
    if rsi > 70 and price > ema:
        # Sobrecopmpra (RSI > 70) E Preço acima da EMA (Tendência forte) -> SINAL DE REVERSÃO
        action = "PUT (VENDA)"
        probability = 0.85
        reason += ". RSI está em sobrecompra e o preço acima da EMA. Esperada reversão."
        
    elif rsi < 30 and price < ema:
        # Sobrevenda (RSI < 30) E Preço abaixo da EMA (Tendência forte) -> SINAL DE REVERSÃO
        action = "CALL (COMPRA)"
        probability = 0.85
        reason += ". RSI está em sobrevenda e o preço abaixo da EMA. Esperada reversão."
        
    # Se nenhuma regra de extremo for acionada, retorna None (sem sinal)
    if action is None:
        return {
            "action": None,
            "probability": 0.0,
            "reason": reason,
            "explanation": "Nenhuma condição de extremo de mercado foi atingida.",
        }

    return {
        "action": action,
        "probability": probability, 
        "reason": reason,
        "explanation": explanation,
    }
