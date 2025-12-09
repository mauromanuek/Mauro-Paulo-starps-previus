# strategy.py
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List

# --- parâmetros / constantes ---
MIN_CANDLES_REQUIRED = 8    # mínimo de candles para avaliar padrões simples
MIN_CANDLES_STRONG = 20    # para indicadores mais confiáveis
MIN_TICK_CONFIRMATION = 1  # usamos last_tick quote para confirmação
RSI_PERIOD = 14

# -------------------------
# helpers
# -------------------------
def candles_to_df(candles: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Converte lista de candle dicts para DataFrame com colunas: open, high, low, close, start_ts
    Assumimos que candles estão ordenadas do mais antigo para o mais recente.
    """
    if not candles:
        return pd.DataFrame()
    df = pd.DataFrame(candles)
    # ensure numeric types
    for col in ["open", "high", "low", "close", "start_ts"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def rsi(series: pd.Series, period: int = RSI_PERIOD) -> Optional[float]:
    if series.size < period + 1:
        return None
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / (avg_loss.replace(0, np.nan))
    last = rs.iloc[-1]
    if pd.isna(last):
        return None
    return 100 - (100 / (1 + last))

def ema(series: pd.Series, span: int) -> Optional[float]:
    if series.size < 2:
        return None
    return float(series.ewm(span=span, adjust=False).mean().iloc[-1])

# price-action patterns
def is_bullish_engulfing(df: pd.DataFrame) -> bool:
    if df.shape[0] < 2:
        return False
    prev = df.iloc[-2]
    cur = df.iloc[-1]
    # prev is red, cur is green and body engulfs
    prev_body = abs(prev['close'] - prev['open'])
    cur_body = abs(cur['close'] - cur['open'])
    return (prev['close'] < prev['open']) and (cur['close'] > cur['open']) and (cur['open'] < prev['close']) and (cur['close'] > prev['open']) and (cur_body > prev_body * 0.5)

def is_bearish_engulfing(df: pd.DataFrame) -> bool:
    if df.shape[0] < 2:
        return False
    prev = df.iloc[-2]
    cur = df.iloc[-1]
    prev_body = abs(prev['close'] - prev['open'])
    cur_body = abs(cur['close'] - cur['open'])
    return (prev['close'] > prev['open']) and (cur['close'] < cur['open']) and (cur['open'] > prev['close']) and (cur['close'] < prev['open']) and (cur_body > prev_body * 0.5)

def is_pinbar(df: pd.DataFrame, ratio: float = 2.5) -> Optional[str]:
    """
    Detecta pinbar no candle mais recente.
    Retorna 'bull' ou 'bear' ou None.
    ratio: relação entre corpo e pavio exigida.
    """
    if df.shape[0] < 1:
        return None
    c = df.iloc[-1]
    body = abs(c['close'] - c['open'])
    upper_wick = c['high'] - max(c['close'], c['open'])
    lower_wick = min(c['close'], c['open']) - c['low']
    # evitar division by zero
    if body <= 0:
        return None
    if lower_wick / body >= ratio and upper_wick / body < (ratio/2):
        return 'bull'
    if upper_wick / body >= ratio and lower_wick / body < (ratio/2):
        return 'bear'
    return None

# -------------------------
# strategy core
# -------------------------
def generate_signal(symbol: str, gran: int, candles: List[Dict[str, Any]], last_tick: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Entrada:
      - symbol: 'R_100' etc
      - gran: granularidade em segundos (e.g., 60)
      - candles: lista de candle dicts (old -> recent)
      - last_tick: {"symbol": symbol, "quote": price}
    Retorna:
      - dict com keys: action, probability, reason, explanation, symbol, tf
      - ou None se sem sinal
    """

    # sanity
    if not candles or len(candles) < MIN_CANDLES_REQUIRED:
        return None

    df = candles_to_df(candles)
    if df.empty:
        return None

    # last price - from tick if available else last candle close
    tick_price = None
    if last_tick and last_tick.get("quote"):
        try:
            tick_price = float(last_tick.get("quote"))
        except Exception:
            tick_price = None
    last_close = float(df['close'].iloc[-1])
    price_for_confirm = tick_price if tick_price is not None else last_close

    # indicators
    close_series = df['close']
    rsi_val = rsi(close_series, period=RSI_PERIOD)
    ema10 = ema(close_series, span=10)
    ema50 = ema(close_series, span=50)

    reasons = []
    probability = 0.5  # base

    # Pattern detection
    bull_engulf = is_bullish_engulfing(df)
    bear_engulf = is_bearish_engulfing(df)
    pin = is_pinbar(df, ratio=2.5)

    # Trend: simple HH/HL or LH/LL using last few closes
    trend = None
    if len(close_series) >= 4:
        last3 = close_series.iloc[-4:]
        if (last3.iloc[-1] > last3.iloc[-2] > last3.iloc[-3]):
            trend = "up"
        elif (last3.iloc[-1] < last3.iloc[-2] < last3.iloc[-3]):
            trend = "down"

    # RULES: combine signals

    action = None

    # Strong bullish conditions:
    # - bullish engulfing OR pinbar bull OR RSI < 30 with price near lower wick + EMA alignment
    if bull_engulf:
        reasons.append("Bullish Engulfing detectado")
        probability += 0.20

    if pin == 'bull':
        reasons.append("Pinbar de alta detectado")
        probability += 0.12

    if rsi_val is not None and rsi_val < 30:
        reasons.append(f"RSI baixo ({rsi_val:.1f})")
        probability += 0.10

    if ema10 and ema50 and ema10 > ema50:
        reasons.append("EMA10 acima da EMA50 (tendência de alta)")
        probability += 0.08

    # Strong bearish
    if bear_engulf:
        reasons.append("Bearish Engulfing detectado")
        probability -= 0.20

    if pin == 'bear':
        reasons.append("Pinbar de baixa detectado")
        probability -= 0.12

    if rsi_val is not None and rsi_val > 70:
        reasons.append(f"RSI alto ({rsi_val:.1f})")
        probability -= 0.10

    if ema10 and ema50 and ema10 < ema50:
        reasons.append("EMA10 abaixo da EMA50 (tendência de baixa)")
        probability -= 0.08

    # Decide action by final probability biases and confirmation by tick
    # normalize probability to 0..1
    prob = max(0.01, min(0.99, probability))

    # Confirmation: if price_for_confirm moves in direction of candle signal, increase confidence
    # We'll base direction on last candle
    last_candle = df.iloc[-1]
    candle_dir = "bull" if last_candle['close'] > last_candle['open'] else "bear" if last_candle['close'] < last_candle['open'] else "neutral"

    confirm_score = 0.0
    if price_for_confirm is not None:
        if candle_dir == "bull" and price_for_confirm >= last_candle['close']:
            confirm_score += 0.06
        if candle_dir == "bear" and price_for_confirm <= last_candle['close']:
            confirm_score += 0.06

    # Final probability adjust
    prob = prob + confirm_score
    prob = max(0.01, min(0.99, prob))

    # Heuristic thresholds to emit signal
    # If biased positive and patterns indicate bullish -> CALL
    bullish_score = 0
    bearish_score = 0
    if bull_engulf or pin == 'bull' or (rsi_val is not None and rsi_val < 35):
        bullish_score += 1
    if bear_engulf or pin == 'bear' or (rsi_val is not None and rsi_val > 65):
        bearish_score += 1

    # Use trend as tie-breaker
    if bullish_score > bearish_score and prob > 0.55:
        action = "CALL"
    elif bearish_score > bullish_score and prob < 0.45:
        action = "PUT"
    else:
        # no clear pattern -> return None
        return None

    # Compose reason and explanation
    reason = "; ".join(reasons) if reasons else "Condições não específicas, confirmação por candle/tick."
    explanation = (
        f"Sinal gerado combinando price-action e indicadores. "
        f"Indicadores: RSI={rsi_val:.2f} " if rsi_val is not None else "RSI=N/A "
    )
    explanation += f"EMA10={ema10:.4f} EMA50={ema50:.4f} " if ema10 and ema50 else ""

    return {
        "action": action,
        "probability": float(round(prob, 3)),
        "symbol": symbol,
        "tf": gran,
        "reason": reason,
        "explanation": explanation,
        "generated_at": int(time.time())
    }
