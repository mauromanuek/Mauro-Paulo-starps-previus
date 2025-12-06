# strategy.py

# Funções de análise
def ema(values, period):
    if len(values) < 1:
        return 0
    k = 2 / (period + 1)
    e = values[0]
    for v in values[1:]:
        e = v * k + e * (1 - k)
    return e

def rsi(values, period=14):
    if len(values) < period + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        if delta > 0:
            gains.append(delta)
        else:
            losses.append(abs(delta))

    avg_gain = sum(gains[-period:]) / max(1, len(gains[-period:]))
    avg_loss = sum(losses[-period:]) / max(1, len(losses[-period:]))
    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)

def generate_signal(closes, policy):
    if len(closes) < 10:
        return None, 0, "Poucos dados"

    ema_fast = ema(closes[-10:], 10)
    ema_slow = ema(closes[-30:], 30)
    r = rsi(closes)

    if ema_fast > ema_slow and r > 55:
        action = "CALL"
        prob = 0.65 + (r - 55) / 100
    elif ema_fast < ema_slow and r < 45:
        action = "PUT"
        prob = 0.65 + (45 - r) / 100
    else:
        action = None
        prob = 0
        reason = "Aguardando sinal claro"
    
    if action:
        reason = f"EMA(10)={ema_fast:.2f}, EMA(30)={ema_slow:.2f}, RSI={r:.2f}"
    
    return action, prob, reason

# CLASSE ESSENCIAL PARA RESOLVER O IMPORTERROR
class Strategy:
    """
    Classe definida para satisfazer a importação em main.py.
    """
    pass
    
