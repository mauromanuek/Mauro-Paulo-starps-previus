# strategy.py - Versão Final de Alta Frequência (Momentum Fallback)

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List

# --- VARIÁVEIS GLOBAIS ---
# Esta lista é preenchida pelo DerivClient.py (após a correção de indentação)
ticks_history: List[float] = [] 


# --- PARÂMETROS OTIMIZADOS DA ESTRATÉGIA ---
RSI_PERIOD = 14
ADX_PERIOD = 14
EMA_FAST_PERIOD = 5
EMA_SLOW_PERIOD = 20
RSI_SELL_THRESHOLD = 70      # Limites otimizados para mais frequência
RSI_BUY_THRESHOLD = 30       # Limites otimizados para mais frequência
ADX_TREND_THRESHOLD = 20     # Limite de Tendência otimizado
MIN_TICKS_REQUIRED = 30      


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

    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs.fillna(0))) 
    
    return rsi.iloc[-1]

def calculate_adx(prices: pd.Series, period: int = ADX_PERIOD) -> float:
    """Simula o ADX (força da tendência) através do desvio da EMA."""
    if len(prices) < period: return np.nan
    
    prices_subset = prices.iloc[-50:] 
    
    ema = prices_subset.ewm(span=period, adjust=False).mean()
    residues = (prices_subset - ema).abs()
    
    adx_proxy = residues.mean() * 10
    
    return min(adx_proxy, 45.0) 


# --- 2. FUNÇÃO PRINCIPAL DE CÁLCULO ---
def calculate_indicators() -> Optional[Dict[str, Any]]:
    """Calcula todos os indicadores necessários para a estratégia adaptativa."""
    global ticks_history
    
    if len(ticks_history) < MIN_TICKS_REQUIRED:
        return None

    prices = pd.Series(ticks_history[-100:]) 
    
    ema_fast = calculate_ema(prices, EMA_FAST_PERIOD)
    ema_slow = calculate_ema(prices, EMA_SLOW_PERIOD)
    adx = calculate_adx(prices, ADX_PERIOD)
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


# --- 3. FUNÇÃO DE SINAL (LÓGICA ADAPTATIVA FINAL) ---
def generate_signal(symbol: str, tf: str) -> Optional[Dict[str, Any]]:
    """
    Gera um sinal de trading com alta frequência, utilizando Momentum como fallback 
    na zona neutra (30-70) para eliminar o NEUTRO.
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
            action = "NEUTRO" # Manter NEUTRO apenas no ponto exato de crossover
            probability = 0.60 
            reason = f"TENDÊNCIA: ADX ({adx:.2f}) ativo, mas EMAs em confluência. Aguardando o Crossover."
            
    # ----------------------------------------------------------------------
    # 2. ESTADO DE CONSOLIDAÇÃO (ADX <= 20) -> Estratégia de Reversão com Fallback
    # ----------------------------------------------------------------------
    else: 
        
        # A) Sinais Fortes de Reversão (Acertividade Máxima)
        if rsi > RSI_SELL_THRESHOLD: # RSI > 70
            action = "PUT (VENDA)"
            probability = 0.92 # Confiança Máxima na zona de range
            reason = f"CONSOLIDAÇÃO: ADX ({adx:.2f}) baixo. RSI ({rsi:.2f}) em sobrecompra (>70). Reversão esperada."
        elif rsi < RSI_BUY_THRESHOLD: # RSI < 30
            action = "CALL (COMPRA)"
            probability = 0.92
            reason = f"CONSOLIDAÇÃO: ADX ({adx:.2f}) baixo. RSI ({rsi:.2f}) em sobrevenda (<30). Reversão esperada."
        
        # B) 💡 NOVO: Sinais de Momentum Interno (RSI entre 30-70)
        else: 
            if ema_fast > ema_slow:
                action = "CALL (COMPRA)"
                probability = 0.75 # Risco moderado, mas trade ativo
                reason = f"CONSOLIDAÇÃO/NEUTRO: RSI ({rsi:.2f}) neutro, mas usamos o Momentum interno (EMA 5 > EMA 20) como fallback."
            elif ema_fast < ema_slow:
                action = "PUT (VENDA)"
                probability = 0.75
                reason = f"CONSOLIDAÇÃO/NEUTRO: RSI ({rsi:.2f}) neutro, mas usamos o Momentum interno (EMA 5 < EMA 20) como fallback."
            else:
                # Último recurso: Nenhum sinal de direção
                action = "NEUTRO"
                probability = 0.50
                reason = f"CONSOLIDAÇÃO/NEUTRO: Nenhum indicador aponta uma direção (ADX baixo, RSI 50, EMAs iguais). NEUTRO."
            
    # ----------------------------------------------------------------------
    
    explanation = f"ANÁLISE ADAPTATIVA (Frequência Máxima): Mercado classificado como {market_state}. Sinais de momentum interno são usados na zona neutra."

    return {
        "action": action,
        "probability": probability,
        "symbol": symbol,
        "tf": tf,
        "reason": reason,
        "explanation": explanation,
        "generated_at": pd.Timestamp.now().isoformat()
    }
