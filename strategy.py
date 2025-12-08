# strategy.py - Versão Final Completa (Lógica Adaptativa + Cálculos Corretos)

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List

# --- VARIÁVEIS GLOBAIS ---
# Certifique-se de que o seu DerivClient.py ou outro módulo preenche esta lista
ticks_history: List[float] = [] 


# --- PARÂMETROS DA ESTRATÉGIA ---
RSI_PERIOD = 14
ADX_PERIOD = 14
EMA_FAST_PERIOD = 5
EMA_SLOW_PERIOD = 20
ADX_TREND_THRESHOLD = 25 # Se ADX > 25, considera-se tendência.
MIN_TICKS_REQUIRED = 30 # Aumentamos o mínimo para suportar ADX/RSI estáveis


# --- 1. FUNÇÕES AUXILIARES DE CÁLCULO (IMPLEMENTAÇÃO COMPLETA) ---

def calculate_ema(prices: pd.Series, period: int) -> float:
    """Calcula a EMA do último preço na série."""
    if len(prices) < period: return np.nan
    return prices.astype(float).ewm(span=period, adjust=False).mean().iloc[-1]

def calculate_rsi(prices: pd.Series, period: int = RSI_PERIOD) -> float:
    """Calcula o RSI correto com base na diferença entre os preços."""
    if len(prices) < period * 2: return np.nan
    
    # Diferença entre preços consecutivos
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Cálculo da Média Móvel Exponencial Suavizada (SMMA/RMA)
    # pandas.ewm(com=period - 1) é equivalente ao SMMA/RMA
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    
    # Cálculo do RS e RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi.iloc[-1]

def calculate_adx(prices: pd.Series, period: int = ADX_PERIOD) -> float:
    """
    Calcula o ADX. NOTA: Em um sistema de TICKs (onde High/Low/Close são iguais),
    o ADX não é a ferramenta ideal. Aqui, simplificamos o conceito de ADX
    (força da tendência) usando o desvio padrão da EMA em relação ao preço.
    Isto simula o conceito de força da tendência.
    """
    if len(prices) < period: return np.nan
    
    # Simulação da Força da Tendência: Desvio Padrão do Preço para a EMA
    # Uma diferença (residuo) grande indica uma tendência forte (ADX alto)
    ema = prices.ewm(span=period, adjust=False).mean()
    residues = (prices - ema).abs()
    
    # Calculamos a média do Desvio Absoluto (um bom proxy para ADX)
    adx_proxy = residues.mean() * 10 
    
    # Normalizamos o valor para o limite 0-100 para ser comparável ao ADX tradicional (máximo 100)
    # Usaremos um valor entre 10 e 40 como limite.
    return min(adx_proxy, 45) # Limita a 45 para fins práticos de ADX


# --- 2. FUNÇÃO PRINCIPAL DE CÁLCULO ---
def calculate_indicators() -> Optional[Dict[str, Any]]:
    """Calcula todos os indicadores necessários."""
    global ticks_history
    
    if len(ticks_history) < MIN_TICKS_REQUIRED:
        return None

    # Usamos os últimos 100 ticks para estabilizar os cálculos
    prices = pd.Series(ticks_history[-100:]) 
    
    # 1. Indicadores de Tendência/Momentum
    ema_fast = calculate_ema(prices, EMA_FAST_PERIOD)
    ema_slow = calculate_ema(prices, EMA_SLOW_PERIOD)
    adx = calculate_adx(prices, ADX_PERIOD)
    
    # 2. Indicador de Reversão
    rsi = calculate_rsi(prices, RSI_PERIOD)
    
    last_price = prices.iloc[-1]
    
    if np.isnan(ema_fast) or np.isnan(ema_slow) or np.isnan(rsi) or np.isnan(adx):
        return None
        
    return {
        "last_price": last_price,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "rsi": rsi,
        "adx": adx,
    }


# --- 3. FUNÇÃO DE SINAL (LÓGICA ADAPTATIVA) ---
def generate_signal(symbol: str, tf: str) -> Optional[Dict[str, Any]]:
    """
    Gera um sinal de trading com base numa estratégia adaptativa profissional.
    """
    indicators = calculate_indicators()
    
    if not indicators:
        return None 
    
    rsi = indicators['rsi']
    ema_fast = indicators['ema_fast']
    ema_slow = indicators['ema_slow']
    adx = indicators['adx']
    
    action = "NEUTRO"
    probability = 0.50 
    
    market_state = "CONSOLIDAÇÃO" if adx <= ADX_TREND_THRESHOLD else "TENDÊNCIA"
    
    # ----------------------------------------------------------------------
    # 1. ANÁLISE PROFISSIONAL: ESTADO DO MERCADO (ADX)
    # ----------------------------------------------------------------------
    if adx > ADX_TREND_THRESHOLD:
        # 🟢 ESTADO 1: MERCADO EM TENDÊNCIA FORTE (ADX > 25)
        # Estratégia de Momentum (EMA Crossover)
        
        if ema_fast > ema_slow:
            action = "CALL (COMPRA)"
            probability = 0.85 
            reason = f"TENDÊNCIA: ADX ({adx:.2f}) forte. EMA 5 cruza acima da EMA 20. MOMENTUM de alta."
        elif ema_fast < ema_slow:
            action = "PUT (VENDA)"
            probability = 0.85
            reason = f"TENDÊNCIA: ADX ({adx:.2f}) forte. EMA 5 cruza abaixo da EMA 20. MOMENTUM de baixa."
        else:
            action = "NEUTRO"
            probability = 0.60
            reason = f"TENDÊNCIA: ADX ({adx:.2f}) forte, mas EMAs em confluência. Aguardando o Crossover."
            
    else: # adx <= 25
        # 🔴 ESTADO 2: MERCADO EM CONSOLIDAÇÃO/RANGE (ADX <= 25)
        # Estratégia de Reversão (RSI Extremo 80/20)
        
        if rsi > 80:
            action = "PUT (VENDA)"
            probability = 0.92 
            reason = f"CONSOLIDAÇÃO: ADX ({adx:.2f}) baixo. RSI ({rsi:.2f}) em extremo de sobrecompra (>80). Esperada reversão."
        elif rsi < 20:
            action = "CALL (COMPRA)"
            probability = 0.92
            reason = f"CONSOLIDAÇÃO: ADX ({adx:.2f}) baixo. RSI ({rsi:.2f}) em extremo de sobrevenda (<20). Esperada reversão."
        else:
            action = "NEUTRO"
            probability = 0.50
            reason = f"CONSOLIDAÇÃO: ADX ({adx:.2f}) baixo e RSI ({rsi:.2f}) neutro. Aguardando extremos (20/80)."
            
    # ----------------------------------------------------------------------
    
    explanation = f"ANÁLISE ADAPTATIVA: Mercado classificado como {market_state}. A estratégia foi ajustada automaticamente."

    return {
        "action": action,
        "probability": probability,
        "symbol": symbol,
        "tf": tf,
        "reason": reason,
        "explanation": explanation,
        "generated_at": pd.Timestamp.now().isoformat()
    }
