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
    Retorna None se não houver dados suficientes.
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

    avg_gain = gain.ewm(com=MAX_TICKS - 1, min_periods=MAX_TICKS).mean()
    avg_loss = loss.ewm(com=MAX_TICKS - 1, min_periods=MAX_TICKS).mean()

    rs = avg_gain / avg_loss
    # O valor final é o último calculado (o mais recente)
    rsi = 100 - (100 / (1 + rs.iloc[-1])) if not pd.isna(rs.iloc[-1]) else None

    # 2. EMA (Exponential Moving Average)
    # Período de 10 ticks para uma EMA rápida
    ema = prices.ewm(span=10, adjust=False).mean().iloc[-1]

    return {
        "rsi": rsi,
        "ema": ema,
        "last_price": prices.iloc[-1]
    }

def generate_signal(symbol: str, tf: str) -> Optional[Dict[str, Any]]:
    """
    Gera um sinal de trading com base nos indicadores calculados.
    """
    indicators = calculate_indicators()
    
    # Se o dicionário de indicadores estiver vazio, a estratégia não pode rodar.
    if not indicators or indicators['rsi'] is None or indicators['ema'] is None:
        # Retorna None. Isso fará com que o main.py retorne 404 (erro) ao frontend.
        return None 
    
    rsi = indicators['rsi']
    ema = indicators['ema']
    price = indicators['last_price']
    
    action = None
    reason = f"RSI: {rsi:.2f}, Preço: {price:.4f}, EMA (10): {ema:.4f}"
    explanation = (
        "O RSI (Índice de Força Relativa) é um indicador de Momentum. "
        "Ele mede a velocidade e a mudança dos movimentos de preço. "
    )
    
    # Regra da Estratégia
    if rsi > 70 and price > ema:
        # RSI acima de 70 (sobrecompra) E preço acima da EMA (tendência de alta forte)
        # Sinais de reversão podem estar próximos. 
        action = "PUT (VENDA)"
        reason += ". RSI está em zona de sobrecompra e o preço está acima da EMA."
        explanation += "Atingiu uma zona extrema e pode reverter para baixo."
        
    elif rsi < 30 and price < ema:
        # RSI abaixo de 30 (sobrevenda) E preço abaixo da EMA (tendência de baixa forte)
        # Sinais de reversão podem estar próximos.
        action = "CALL (COMPRA)"
        reason += ". RSI está em zona de sobrevenda e o preço está abaixo da EMA."
        explanation += "Atingiu uma zona extrema e pode reverter para cima."
        
    # Se nenhuma regra de extremo for acionada, não retorna sinal.
    if action is None:
        return None 

    return {
        "action": action,
        "probability": 0.85, # Valor fixo, mas poderia ser dinâmico
        "symbol": symbol,
        "tf": tf,
        "reason": reason,
        "explanation": explanation,
        "generated_at": pd.Timestamp.now().isoformat()
    }
