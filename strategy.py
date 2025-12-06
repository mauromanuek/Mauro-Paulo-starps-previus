# strategy.py

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
    Retorna um dicionário vazio se não houver dados suficientes.
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

    # Cálculo da Média Exponencial Móvel para RSI (EWMA)
    avg_gain = gain.ewm(com=MAX_TICKS - 1, min_periods=MAX_TICKS).mean()
    avg_loss = loss.ewm(com=MAX_TICKS - 1, min_periods=MAX_TICKS).mean()

    # Previne divisão por zero (ocorre em raras ocasiões)
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs.iloc[-1])) if not pd.isna(rs.iloc[-1]) and avg_loss.iloc[-1] != 0 else None

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
    Gera um sinal de trading com base nos indicadores calculados (versão simplificada para teste).
    """
    indicators = calculate_indicators()
    
    # Se o dicionário de indicadores estiver vazio ou incompleto, a estratégia não pode rodar.
    if not indicators or indicators.get('rsi') is None or indicators.get('ema') is None:
        # Retorna None.
        return None 
    
    rsi = indicators['rsi']
    ema = indicators['ema']
    price = indicators['last_price']
    
    action = None
    probability = 0.85
    reason = f"RSI: {rsi:.2f}, Preço: {price:.4f}, EMA (10): {ema:.4f}"
    explanation = (
        "Estratégia de Reversão Simplificada: Procura zonas extremas de Sobrecompra (>70) ou Sobrevenda (<30) no RSI."
    )

    # 🚨 REGRA SIMPLIFICADA PARA TESTE DE EXECUÇÃO 🚨
    # Apenas exige que o RSI atinja uma zona extrema para gerar um sinal de reversão.
    
    # 1. Sinal de VENDA (PUT)
    if rsi > 70:
        # RSI em sobrecompra (>70): Assinala potencial de reversão para baixo.
        action = "PUT (VENDA)"
        reason += ". RSI em sobrecompra (>70)."
        
    # 2. Sinal de COMPRA (CALL)
    elif rsi < 30:
        # RSI em sobrevenda (<30): Assinala potencial de reversão para cima.
        action = "CALL (COMPRA)"
        reason += ". RSI em sobrevenda (<30)."
        
    # Se nenhuma regra de extremo for acionada, não retorna sinal.
    if action is None:
        return None 

    return {
        "action": action,
        "probability": probability,
        "symbol": symbol,
        "tf": tf,
        "reason": reason,
        "explanation": explanation,
        "generated_at": pd.Timestamp.now().isoformat()
    }
