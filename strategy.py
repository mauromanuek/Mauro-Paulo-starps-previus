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
    # 1. Verifica a quantidade mínima de dados
    if len(ticks_history) < MAX_TICKS:
        return {} 

    # Converte a lista para uma Série Pandas para cálculo de indicadores
    prices = pd.Series(ticks_history)
    
    # 2. RSI (Relative Strength Index)
    # Ajustamos o período para o nosso volume (MAX_TICKS=20)
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Cálculo da Média Móvel Exponencial (EWM)
    # min_periods=MAX_TICKS garante que só teremos um valor numérico quando tivermos 20 pontos.
    avg_gain = gain.ewm(com=MAX_TICKS - 1, min_periods=MAX_TICKS).mean()
    avg_loss = loss.ewm(com=MAX_TICKS - 1, min_periods=MAX_TICKS).mean()

    # Extrai o último valor calculado (índice -1)
    final_avg_gain = avg_gain.iloc[-1]
    final_avg_loss = avg_loss.iloc[-1]

    # Cálculo do RS e RSI
    if final_avg_loss == 0:
        # Se avg_loss for 0, o preço só subiu no período. RSI deve ser 100.
        rs = np.inf
    else:
        rs = final_avg_gain / final_avg_loss

    rsi = 100 - (100 / (1 + rs))
    
    # 3. EMA (Exponential Moving Average)
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
    
    # 🟢 CORREÇÃO CRÍTICA AQUI: Verifica se os dados são insuficientes OU se a primeira tentativa gerou NaN.
    if not indicators: 
        return None # Dados insuficientes (len < 20)
    
    # Extrai indicadores
    rsi = indicators['rsi']
    ema = indicators['ema']
    price = indicators['last_price']
    
    # ✅ NOVO CHECK: Se o Pandas retornou NaN (mesmo com 20 ticks, pode acontecer nos primeiros momentos)
    if pd.isna(rsi) or pd.isna(ema):
        print("[Strategy] DEBUG: RSI ou EMA é NaN, retornando None para re-tentativa.")
        return None 
        
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
        
    # Se nenhuma regra de extremo for acionada, retorna None, o que é um sinal VÁLIDO de 'NÃO HÁ SINAL'
    if action is None:
        # Aqui, decidimos se queremos retornar um 'sem sinal' ou None.
        # Para a lógica atual, vamos retornar um sinal de "NEUTRO" se houver dados, mas sem regra acionada.
        return {
            "action": "NEUTRO (Aguardar)",
            "probability": 0.50,
            "reason": "Condições de mercado neutras ou fora dos extremos do RSI/EMA.",
            "explanation": "Nenhuma das regras de reversão de extremo foi satisfeita. Não operar."
        }
        
    # Se o sinal foi gerado
    return {
        "action": action,
        "probability": 0.85, # Valor fixo para esta fase
        "reason": reason,
        "explanation": explanation
    }
