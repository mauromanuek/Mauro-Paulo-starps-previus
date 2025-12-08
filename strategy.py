# strategy.py - Versão Final com Alerta Explícito de Fecho de Tendência

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List

# --- VARIÁVEIS GLOBAIS ---
ticks_history: List[float] = [] 


# --- PARÂMETROS OTIMIZADOS DA ESTRATÉGIA ---
RSI_PERIOD = 14
ADX_PERIOD = 14
EMA_FAST_PERIOD = 5
EMA_SLOW_PERIOD = 20
EMA_VERY_SLOW_PERIOD = 50    
RSI_SELL_THRESHOLD = 70      
RSI_BUY_THRESHOLD = 30       
ADX_TREND_THRESHOLD = 20     
MIN_TICKS_REQUIRED = 50      


# --- FUNÇÕES AUXILIARES DE CÁLCULO (INALTERADAS) ---

def calculate_ema(prices: pd.Series, period: int) -> float:
    if len(prices) < period: return np.nan
    return prices.astype(float).ewm(span=period, adjust=False).mean().iloc[-1]

def calculate_rsi(prices: pd.Series, period: int = RSI_PERIOD) -> float:
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
    if len(prices) < period: return np.nan
    prices_subset = prices.iloc[-50:] 
    ema = prices_subset.ewm(span=period, adjust=False).mean()
    residues = (prices_subset - ema).abs()
    adx_proxy = residues.mean() * 10
    return min(adx_proxy, 45.0) 


# --- 2. FUNÇÃO PRINCIPAL DE CÁLCULO ---
def calculate_indicators() -> Optional[Dict[str, Any]]:
    global ticks_history
    if len(ticks_history) < MIN_TICKS_REQUIRED: 
        return None

    prices = pd.Series(ticks_history[-150:]) 
    
    ema_fast = calculate_ema(prices, EMA_FAST_PERIOD)
    ema_slow = calculate_ema(prices, EMA_SLOW_PERIOD)
    ema_very_slow = calculate_ema(prices, EMA_VERY_SLOW_PERIOD) 
    adx = calculate_adx(prices, ADX_PERIOD)
    rsi = calculate_rsi(prices, RSI_PERIOD)
    last_price = prices.iloc[-1]
    
    if np.isnan(ema_very_slow) or np.isnan(ema_fast) or np.isnan(ema_slow) or np.isnan(rsi) or np.isnan(adx):
        return None
        
    return {
        "last_price": last_price,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "ema_very_slow": ema_very_slow, 
        "rsi": rsi,
        "adx": adx,
    }


# --- 3. FUNÇÃO DE SINAL (LÓGICA ADAPTATIVA FINAL) ---
def generate_signal(symbol: str, tf: str) -> Optional[Dict[str, Any]]:
    
    indicators = calculate_indicators()
    
    if not indicators:
        return None 
    
    rsi = indicators['rsi']
    ema_fast = indicators['ema_fast']
    ema_slow = indicators['ema_slow']
    ema_very_slow = indicators['ema_very_slow'] 
    adx = indicators['adx']
    last_price = indicators['last_price']
    
    action = "NEUTRO"
    probability = 0.50 
    market_state = "CONSOLIDAÇÃO" if adx <= ADX_TREND_THRESHOLD else "TENDÊNCIA"
    
    # ----------------------------------------------------------------------
    # 1. ESTADO DE TENDÊNCIA (ADX > 20) -> Estratégia de Momentum Filtrada
    # ----------------------------------------------------------------------
    if adx > ADX_TREND_THRESHOLD:
        
        # SINAL DE COMPRA (CALL)
        if ema_fast > ema_slow:
            if last_price > ema_very_slow:
                # Confirmação de Tendência
                action = "CALL (COMPRA)"
                probability = 0.90 
                reason = f"TENDÊNCIA: ADX forte. Momentum de alta (EMA 5 > 20) CONFIRMADO pelo Filtro Macro (Preço > EMA 50)."
            else:
                # 🚨 ALERTA DE FECHO DE TENDÊNCIA 🚨
                action = "NEUTRO" # Segurança (não negociar contra o macro)
                probability = 0.70 
                reason = f"ALERTA DE FECHO DE TENDÊNCIA: A Tendência de Alta primária falhou. O Preço ({last_price:.4f}) quebrou o nível chave EMA 50 ({ema_very_slow:.4f}), indicando o FIM da tendência de alta."

        # SINAL DE VENDA (PUT)
        elif ema_fast < ema_slow:
            if last_price < ema_very_slow:
                # Confirmação de Tendência
                action = "PUT (VENDA)"
                probability = 0.90 
                reason = f"TENDÊNCIA: ADX forte. Momentum de baixa (EMA 5 < 20) CONFIRMADO pelo Filtro Macro (Preço < EMA 50)."
            else:
                # 🚨 ALERTA DE FECHO DE TENDÊNCIA 🚨
                action = "NEUTRO" # Segurança (não negociar contra o macro)
                probability = 0.70 
                reason = f"ALERTA DE FECHO DE TENDÊNCIA: A Tendência de Baixa primária falhou. O Preço ({last_price:.4f}) quebrou o nível chave EMA 50 ({ema_very_slow:.4f}), indicando o FIM da tendência de baixa."
        
        else: # EMAs em confluência no Trend
            action = "NEUTRO" 
            probability = 0.60 
            reason = f"TENDÊNCIA: ADX ativo, mas EMAs em confluência. Aguardando o Crossover."
            
    # ----------------------------------------------------------------------
    # 2. ESTADO DE CONSOLIDAÇÃO (ADX <= 20) -> Lógica Inalterada
    # ----------------------------------------------------------------------
    else: 
        
        # A) Sinais Fortes de Reversão 
        if rsi > RSI_SELL_THRESHOLD: 
            action = "PUT (VENDA)"
            probability = 0.92 
            reason = f"CONSOLIDAÇÃO: ADX baixo. RSI ({rsi:.2f}) em sobrecompra (>70). Reversão esperada."
        elif rsi < RSI_BUY_THRESHOLD: 
            action = "CALL (COMPRA)"
            probability = 0.92
            reason = f"CONSOLIDAÇÃO: ADX baixo. RSI ({rsi:.2f}) em sobrevenda (<30). Reversão esperada."
        
        # B) Sinais de Momentum Interno (RSI entre 30-70)
        elif ema_fast > ema_slow:
            action = "CALL (COMPRA)"
            probability = 0.75 
            reason = f"CONSOLIDAÇÃO/NEUTRO: RSI neutro, mas usamos o Crossover (EMA 5 > EMA 20) como fallback."
        elif ema_fast < ema_slow:
            action = "PUT (VENDA)"
            probability = 0.75
            reason = f"CONSOLIDAÇÃO/NEUTRO: RSI neutro, mas usamos o Crossover (EMA 5 < EMA 20) como fallback."
        
        # C) Fallback Agressivo (Para Quase Eliminar o NEUTRO)
        else:
            if last_price > ema_slow:
                action = "CALL (COMPRA)"
                probability = 0.65
                reason = f"ALTA FREQUÊNCIA: Falha em todos os testes. Forçando a direção: Preço atual está acima da EMA 20."
            elif last_price < ema_slow:
                action = "PUT (VENDA)"
                probability = 0.65
                reason = f"ALTA FREQUÊNCIA: Falha em todos os testes. Forçando a direção: Preço atual está abaixo da EMA 20."
            else:
                action = "NEUTRO" 
                probability = 0.50
                reason = "EXTREMA INDECISÃO: Preço e EMAs estão perfeitamente iguais. NEUTRO."
            
    # ----------------------------------------------------------------------
    
    explanation = f"ANÁLISE ADAPTATIVA: Mercado classificado como {market_state}. A estratégia agora deteta o Fecho de Tendência primária usando a quebra da EMA 50."

    return {
        "action": action,
        "probability": probability,
        "symbol": symbol,
        "tf": tf,
        "reason": reason,
        "explanation": explanation,
        "generated_at": pd.Timestamp.now().isoformat()
    }
