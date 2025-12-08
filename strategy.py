# strategy.py - Versão Final Completa e Otimizada (Lógica Adaptativa)

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List

# --- VARIÁVEIS GLOBAIS ---
# Esta lista é preenchida pelo DerivClient.py (com a correção da linha 116)
ticks_history: List[float] = [] 


# --- PARÂMETROS OTIMIZADOS DA ESTRATÉGIA ---
RSI_PERIOD = 14
ADX_PERIOD = 14
EMA_FAST_PERIOD = 5
EMA_SLOW_PERIOD = 20
RSI_SELL_THRESHOLD = 70      # OTIMIZADO: Mais sinais de reversão
RSI_BUY_THRESHOLD = 30       # OTIMIZADO: Mais sinais de reversão
ADX_TREND_THRESHOLD = 20     # OTIMIZADO: Reconhece tendências mais fracas
MIN_TICKS_REQUIRED = 30      # Mínimo de ticks para cálculos estáveis


# --- 1. FUNÇÕES AUXILIARES DE CÁLCULO ---

def calculate_ema(prices: pd.Series, period: int) -> float:
    """Calcula a EMA do último preço na série."""
    if len(prices) < period: return np.nan
    return prices.astype(float).ewm(span=period, adjust=False).mean().iloc[-1]

def calculate_rsi(prices: pd.Series, period: int = RSI_PERIOD) -> float:
    """Calcula o RSI com base na diferença entre os preços."""
    if len(prices) < period * 2: return np.nan
    
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Cálculo da Média Móvel Exponencial Suavizada (SMMA/RMA)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    # Evitar divisão por zero se avg_loss for 0
    rsi = 100 - (100 / (1 + rs.fillna(0))) 
    
    return rsi.iloc[-1]

def calculate_adx(prices: pd.Series, period: int = ADX_PERIOD) -> float:
    """
    Simula o cálculo do ADX (força da tendência) através do desvio da EMA.
    (Proxy necessária para mercados de tick sem dados de High/Low/Volume).
    """
    if len(prices) < period: return np.nan
    
    # Média dos últimos 50 ticks para estabilidade no cálculo
    prices_subset = prices.iloc[-50:] 
    
    # Calcula o desvio padrão do preço em relação à sua média móvel
    ema = prices_subset.ewm(span=period, adjust=False).mean()
    residues = (prices_subset - ema).abs()
    
    # ADX Proxy: Média do Desvio Absoluto, normalizada para 0-45
    adx_proxy = residues.mean() * 10
    
    return min(adx_proxy, 45.0) # Limita o proxy para ser comparável ao ADX (máx. 100)


# --- 2. FUNÇÃO PRINCIPAL DE CÁLCULO ---
def calculate_indicators() -> Optional[Dict[str, Any]]:
    """Calcula todos os indicadores necessários para a estratégia adaptativa."""
    global ticks_history
    
    if len(ticks_history) < MIN_TICKS_REQUIRED:
        return None

    # Usamos os últimos 100 ticks para estabilizar os cálculos
    prices = pd.Series(ticks_history[-100:]) 
    
    # Indicadores
    ema_fast = calculate_ema(prices, EMA_FAST_PERIOD)
    ema_slow = calculate_ema(prices, EMA_SLOW_PERIOD)
    adx = calculate_adx(prices, ADX_PERIOD)
    rsi = calculate_rsi(prices, RSI_PERIOD)
    last_price = prices.iloc[-1]
    
    # Verifica se todos os cálculos foram bem-sucedidos
    if np.isnan(ema_fast) or np.isnan(ema_slow) or np.isnan(rsi) or np.isnan(adx):
        return None
        
    return {
        "last_price": last_price,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "rsi": rsi,
        "adx": adx,
    }


# --- 3. FUNÇÃO DE SINAL (LÓGICA ADAPTATIVA OTIMIZADA) ---
def generate_signal(symbol: str, tf: str) -> Optional[Dict[str, Any]]:
    """
    Gera um sinal de trading com base na estratégia adaptativa (ADX, Crossover, RSI 30/70).
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
    # 1. ESTADO DE TENDÊNCIA (ADX > 20) -> Estratégia de Momentum
    # ----------------------------------------------------------------------
    if adx > ADX_TREND_THRESHOLD:
        
        if ema_fast > ema_slow:
            action = "CALL (COMPRA)"
            probability = 0.85 
            reason = f"TENDÊNCIA: ADX ({adx:.2f}) indica força. EMA 5 > EMA 20. MOMENTUM de alta."
        elif ema_fast < ema_slow:
            action = "PUT (VENDA)"
            probability = 0.85
            reason = f"TENDÊNCIA: ADX ({adx:.2f}) indica força. EMA 5 < EMA 20. MOMENTUM de baixa."
        else:
            # Em tendência forte, mas sem crossover claro.
            action = "NEUTRO" 
            probability = 0.60 
            reason = f"TENDÊNCIA: ADX ({adx:.2f}) ativo, mas EMAs em confluência. Aguardando o Crossover."
            
    # ----------------------------------------------------------------------
    # 2. ESTADO DE CONSOLIDAÇÃO (ADX <= 20) -> Estratégia de Reversão
    # ----------------------------------------------------------------------
    else: 
        
        if rsi > RSI_SELL_THRESHOLD: # NOVO LIMITE: 70
            action = "PUT (VENDA)"
            probability = 0.88 
            reason = f"CONSOLIDAÇÃO: ADX ({adx:.2f}) baixo. RSI ({rsi:.2f}) em sobrecompra (>70). Reversão esperada."
        elif rsi < RSI_BUY_THRESHOLD: # NOVO LIMITE: 30
            action = "CALL (COMPRA)"
            probability = 0.88
            reason = f"CONSOLIDAÇÃO: ADX ({adx:.2f}) baixo. RSI ({rsi:.2f}) em sobrevenda (<30). Reversão esperada."
        else:
            action = "NEUTRO"
            probability = 0.50
            reason = f"CONSOLIDAÇÃO: ADX ({adx:.2f}) baixo e RSI ({rsi:.2f}) neutro (30-70). Aguardando extremos."
            
    # ----------------------------------------------------------------------
    
    explanation = f"ANÁLISE ADAPTATIVA (Frequência Otimizada): Mercado classificado como {market_state}."

    return {
        "action": action,
        "probability": probability,
        "symbol": symbol,
        "tf": tf,
        "reason": reason,
        "explanation": explanation,
        "generated_at": pd.Timestamp.now().isoformat()
    }
