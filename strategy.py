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
    Retorna dicionário vazio se não houver dados suficientes.
    """
    # 1. Detetor de Erro: Falta de Ticks
    if len(ticks_history) < MAX_TICKS:
        print(f"[Strategy:Indicators] ⚠️ Dados insuficientes: {len(ticks_history)}/{MAX_TICKS} ticks. Retornando vazio.")
        return {} 

    # Converte a lista para uma Série Pandas para cálculo de indicadores
    prices = pd.Series(ticks_history)
    
    # 2. RSI (Relative Strength Index)
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Cálculo da Média Móvel Exponencial (EWM)
    avg_gain = gain.ewm(com=MAX_TICKS - 1, min_periods=MAX_TICKS).mean()
    avg_loss = loss.ewm(com=MAX_TICKS - 1, min_periods=MAX_TICKS).mean()

    # Extrai o último valor calculado (índice -1)
    final_avg_gain = avg_gain.iloc[-1]
    final_avg_loss = avg_loss.iloc[-1]

    # Cálculo do RS e RSI
    if final_avg_loss == 0:
        rs = np.inf
    else:
        rs = final_avg_gain / final_avg_loss

    rsi = 100 - (100 / (1 + rs))
    
    # 3. EMA (Exponential Moving Average)
    # span=10 é o período de cálculo.
    ema = prices.ewm(span=10, adjust=False).mean().iloc[-1]
    
    return {
        "rsi": rsi,
        "ema": ema,
        "last_price": prices.iloc[-1]
    }

def generate_signal(symbol: str, tf: str) -> Optional[Dict[str, Any]]:
    """
    Gera um sinal de trading (CALL/PUT) com base nos indicadores calculados.
    """
    indicators = calculate_indicators()
    
    # O log de falta de ticks já foi gerado dentro de calculate_indicators
    if not indicators: 
        return None 
    
    # Extrai indicadores
    rsi = indicators['rsi']
    ema = indicators['ema']
    price = indicators['last_price']
    
    # 2. Detetor de Erro: Valores Não Numéricos (NaN)
    if pd.isna(rsi) or pd.isna(ema):
        print(f"[Strategy:Signal] ❌ ERRO de Cálculo (NaN). RSI={rsi}, EMA={ema}. Retornando None para re-tentativa.")
        return None 
        
    action = None
    reason = f"RSI: {rsi:.2f}, Preço: {price:.4f}, EMA (10): {ema:.4f}"
    explanation = (
        "O RSI (Índice de Força Relativa) é um indicador de Momentum. "
        "Ele mede a velocidade e a mudança dos movimentos de preço. "
    )
    
    # Regra da Estratégia
    if rsi > 70 and price > ema:
        action = "PUT (VENDA)"
        reason += ". RSI está em zona de sobrecompra e o preço está acima da EMA."
        explanation += "Atingiu uma zona extrema e pode reverter para baixo."
        
    elif rsi < 30 and price < ema:
        action = "CALL (COMPRA)"
        reason += ". RSI está em zona de sobrevenda e o preço está abaixo da EMA."
        explanation += "Atingiu uma zona extrema e pode reverter para cima."
        
    if action is None:
        # 3. Detetor de Sucesso: Não Encontrou Regra (NEUTRO)
        print(f"[Strategy:Signal] 🟦 Sinal NEUTRO. Indicadores: RSI={rsi:.2f}, EMA={ema:.4f}.")
        return {
            "action": "NEUTRO (Aguardar)",
            "probability": 0.50,
            "reason": "Condições de mercado neutras ou fora dos extremos do RSI/EMA.",
            "explanation": "Nenhuma das regras de reversão de extremo foi satisfeita. Não operar."
        }
        
    # 4. Detetor de Sucesso: Sinal Encontrado
    print(f"[Strategy:Signal] ✅ Sinal Encontrado: {action}")
    return {
        "action": action,
        "probability": 0.85, # Valor fixo para esta fase
        "reason": reason,
        "explanation": explanation
    }
