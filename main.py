import os
import threading
import json
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from websocket import create_connection
import pandas as pd
import numpy as np
# --- IMPORTAÇÃO CRÍTICA FALTANDO (CORREÇÃO) ---
from werkzeug.serving import make_server
# -----------------------------------------------

# --- CONFIGURAÇÕES DE APLICAÇÃO ---
MY_APP_ID = 114910 
DERIV_URL = f"wss://ws.derivws.com/websockets/v3?app_id={MY_APP_ID}"
FIXED_TRADE_DURATION_SECONDS = 300 # 5 minutos (Granularidade 5m)
MAX_LOG_SIZE = 50 
S_R_LOOKBACK = 20 # Período para análise de S/R

# --- VARIÁVEIS GLOBAIS DE ESTADO ---
app = Flask(__name__)
BOT_STATUS = "OFF"
BOT_THREAD = None
LOG_MESSAGES = [] 
CURRENT_SYMBOL = "R_100" 

# Estrutura do Sinal Final
FINAL_SIGNAL_DATA = {
    'direction': 'AGUARDANDO', 
    'trend': 'Análise de Velas', 
    'entry_time': '--:--:--', 
    'exit_time': '--:--:--',
    'confidence': 0,
    'indicator_status': 'EMA: --, Stoch: --, RSI: --',
    'justification': 'O bot está inativo ou a aguardar a análise inicial de mercado.',
    'strategy_used': 'Nenhuma',
    'tf': '5m'
}

# --- FUNÇÕES DE UTENSÍLIO E LOGS ---

def safe_float(value):
    """Converte para float com segurança."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return np.nan

def add_log(message):
    """Adiciona uma mensagem à lista global de logs (Render/Frontend)."""
    global LOG_MESSAGES
    timestamp = time.strftime('%H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    LOG_MESSAGES.append(log_entry)
    if len(LOG_MESSAGES) > MAX_LOG_SIZE:
        LOG_MESSAGES.pop(0)
    print(log_entry) 

def update_signal_data(data):
    """Atualiza a variável global do sinal com segurança."""
    global FINAL_SIGNAL_DATA
    FINAL_SIGNAL_DATA.update(data)

def connect_ws(url, api_token):
    """Cria e autentica a conexão WebSocket."""
    ws = create_connection(url)
    cleaned_token = api_token.strip() 
    ws.send(json.dumps({"authorize": cleaned_token})) 
    auth_response = json.loads(ws.recv())
    
    if auth_response.get('error'):
        raise Exception(f"Erro de Autenticação: {auth_response['error']['message']}")
    
    return ws

# --- CÁLCULO DE INDICADORES (NOVOS FILTROS INCLUÍDOS) ---

def calculate_ema(series, length):
    """Calcula a Média Móvel Exponencial (EMA)."""
    return series.ewm(span=length, adjust=False).mean()

def calculate_rsi(df, length=14):
    """Calcula o Índice de Força Relativa (RSI)."""
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.ewm(com=length - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=length - 1, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan) 
    rsi = 100 - (100 / (1 + rs))
    df[f'RSI_{length}'] = rsi
    return df

def calculate_bbands(df, length=20, std_dev=2):
    """Calcula as Bandas de Bollinger (BBands)."""
    df[f'SMA_{length}'] = df['Close'].rolling(window=length).mean()
    df[f'StdDev_{length}'] = df['Close'].rolling(window=length).std()
    
    df[f'BBU_{length}_{std_dev}.0'] = df[f'SMA_{length}'] + (df[f'StdDev_{length}'] * std_dev)
    df[f'BBL_{length}_{std_dev}.0'] = df[f'SMA_{length}'] - (df[f'StdDev_{length}'] * std_dev)
    
    return df

def calculate_stoch(df, k_length=14, d_length=3):
    """Calcula o Stochastic Oscillator."""
    low_min = df['Low'].rolling(window=k_length).min()
    high_max = df['High'].rolling(window=k_length).max()
    
    range_diff = high_max - low_min
    range_diff.replace(0, np.nan, inplace=True) 
    
    df['%K'] = 100 * (df['Close'] - low_min) / range_diff
    df[f'STOCHk_{k_length}_{d_length}_{d_length}'] = df['%K'].rolling(window=d_length).mean() 
    return df

# NOVO FILTRO DE ASSERTIVIDADE 1: ATR (Volatilidade)
def calculate_atr(df, length=14):
    """Calcula o Average True Range (ATR) para filtrar mercados estagnados."""
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift(1))
    low_close = np.abs(df['Low'] - df['Close'].shift(1))
    
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(span=length, adjust=False).mean()
    return df

# NOVO FILTRO DE ASSERTIVIDADE 2: FRACTALS (S/R Dinâmico)
def calculate_fractals(df):
    """Identifica fractais de alta e baixa para zonas dinâmicas de S/R. """
    
    # Fractal de Baixa (Potencial Suporte)
    is_low_fractal = (df['Low'].shift(2) > df['Low'].shift(1)) & \
                     (df['Low'].shift(1) > df['Low']) & \
                     (df['Low'] < df['Low'].shift(-1)) & \
                     (df['Low'].shift(-1) < df['Low'].shift(-2))
    df.loc[is_low_fractal.shift(2).fillna(False), 'Low_Fractal'] = df['Low'].shift(2)
    
    # Fractal de Alta (Potencial Resistência)
    is_high_fractal = (df['High'].shift(2) < df['High'].shift(1)) & \
                      (df['High'].shift(1) < df['High']) & \
                      (df['High'] > df['High'].shift(-1)) & \
                      (df['High'].shift(-1) > df['High'].shift(-2))
    df.loc[is_high_fractal.shift(2).fillna(False), 'High_Fractal'] = df['High'].shift(2)
    
    return df


# --- LÓGICA DE DETECÇÃO E CONFIRMAÇÃO ---

def detect_candlestick_pattern(df):
    """Detecta padrões de candlestick (Martelo, Estrela Cadente, Engolfo)."""
    # (Função de detecção original mantida)
    if len(df) < 2: return 0
        
    c = df.iloc[-1] 
    p = df.iloc[-2] 
    
    range_c = c['High'] - c['Low']
    body_c = abs(c['Close'] - c['Open'])

    if range_c == 0 or range_c < 0.00001: return 0

    is_small_body = body_c < 0.3 * range_c
    
    # Martelo / Estrela Cadente
    lower_shadow_c = min(c['Open'], c['Close']) - c['Low']
    is_hammer = is_small_body and (lower_shadow_c > 2 * body_c)
    if is_hammer: return 100 

    upper_shadow_c = c['High'] - max(c['Open'], c['Close'])
    is_shooting_star = is_small_body and (upper_shadow_c > 2 * body_c)
    if is_shooting_star: return -100 

    # Engolfo
    range_p = p['High'] - p['Low']
    body_p = abs(p['Close'] - p['Open'])
    
    is_bear_engulf = (c['Close'] < c['Open']) and (p['Close'] > p['Open']) and \
                     (c['Open'] > p['Close']) and (c['Close'] < p['Open']) and \
                     (body_c > body_p) 

    is_bull_engulf = (c['Close'] > c['Open']) and (p['Close'] < p['Open']) and \
                     (c['Open'] < p['Close']) and (c['Close'] > p['Open']) and \
                     (body_c > body_p)

    if is_bear_engulf: return -100
    if is_bull_engulf: return 100

    return 0 

def check_confirmation(df, current_close):
    """
    Verifica a confirmação do sinal perto de zonas dinâmicas de S/R (usando Fractals).
    """
    df_fractals = calculate_fractals(df.copy())
    
    # Zonas de S/R Recentes (Últimos 20 períodos)
    recent_low = df_fractals['Low_Fractal'].iloc[-S_R_LOOKBACK:].dropna().max()
    recent_high = df_fractals['High_Fractal'].iloc[-S_R_LOOKBACK:].dropna().min()
    
    # Margem de Confirmação (ATR como filtro dinâmico)
    atr_margin = df['ATR'].iloc[-1] * 1.5 if not df['ATR'].empty and not np.isnan(df['ATR'].iloc[-1]) else 0.0001
    
    pattern_val = detect_candlestick_pattern(df) 
    is_bullish_pattern = (pattern_val > 0)
    is_bearish_pattern = (pattern_val < 0)
            
    conf_call, conf_put = "", ""
    
    # 1. Confirmação CALL (Perto do Suporte/Low Fractal)
    if not np.isnan(recent_low) and current_close <= recent_low + atr_margin:
        conf_call = "Suporte"
        if is_bullish_pattern:
            conf_call = "Forte: Candlestick Bullish na Zona de Suporte."
        
    # 2. Confirmação PUT (Perto da Resistência/High Fractal)
    if not np.isnan(recent_high) and current_close >= recent_high - atr_margin:
        conf_put = "Resistência"
        if is_bearish_pattern:
            conf_put = "Forte: Candlestick Bearish na Zona de Resistência."
            
    return conf_call, conf_put, recent_low, recent_high


# --- ESTRATÉGIA: MOTOR DE SELEÇÃO E DECISÃO ---

def strategy_selection_engine(df, granularity_minutes):
    """
    Motor Central de Estratégias de Extremo e Reversão (Otimizado para Assertividade).
    """
    
    # 1. Obter valores recentes
    current_close = df['Close'].iloc[-1]
    current_ema = df['EMA_10'].iloc[-1]
    current_stoch_k = df['STOCHk_14_3_3'].iloc[-1]
    
    current_rsi = df['RSI_14'].iloc[-1]
    bbands_upper = df['BBU_20_2.0'].iloc[-1]
    bbands_lower = df['BBL_20_2.0'].iloc[-1]
    
    current_atr = df['ATR'].iloc[-1]
    ATR_MIN_LIMIT = 0.00005 # Limite de Volatilidade Mínima para negociar

    # Obter Confirmação de S/R (String de Justificação)
    conf_call_str, conf_put_str, _, _ = check_confirmation(df, current_close)
    
    # Booleans para fácil leitura
    is_conf_call = bool(conf_call_str)
    is_conf_put = bool(conf_put_str)
    
    # Status dos Indicadores
    ema_status = f"{current_ema:.4f}" if not np.isnan(current_ema) else "--"
    rsi_status = f"{current_rsi:.2f}" if not np.isnan(current_rsi) else "--"
    indicator_status = f"EMA(10): {ema_status}, Stoch K: {current_stoch_k:.2f}, RSI: {rsi_status}, ATR: {current_atr:.5f}" 
    
    # Preparações padrão
    trend, confidence, strategy_used = "NEUTRA", 40, "Análise de Contexto"
    justification = "Mercado Neutro ou sem sinais de alta confiança."
    
    # --- FILTRO DE ASSERTIVIDADE ATR (PRIORIDADE MÁXIMA) ---
    if not np.isnan(current_atr) and current_atr < ATR_MIN_LIMIT:
        return "NEUTRA", f"FILTRADO POR ATR: Volatilidade muito baixa ({current_atr:.5f} < {ATR_MIN_LIMIT}). Mercado estagnado.", 5, indicator_status, "Filtro de Volatilidade ATR"
    # --------------------------------------------------------

    # --- 1. ESTRATÉGIA MÁXIMA: BBands Extremo (90%) ---
    if not np.isnan(bbands_upper) and current_close > bbands_upper and is_conf_put:
        strategy_used = "BBANDS Reversão (Extremo + S/R) [attachment_0](attachment)"
        trend = "PUT"
        confidence = 90
        justification = f"REVERSÃO FORTE (90%). Preço acima da Banda Superior. CONFIRMAÇÃO: {conf_put_str}."
        return trend, justification, confidence, indicator_status, strategy_used

    if not np.isnan(bbands_lower) and current_close < bbands_lower and is_conf_call:
        strategy_used = "BBANDS Reversão (Extremo + S/R)"
        trend = "CALL"
        confidence = 90
        justification = f"REVERSÃO FORTE (90%). Preço abaixo da Banda Inferior. CONFIRMAÇÃO: {conf_call_str}."
        return trend, justification, confidence, indicator_status, strategy_used
        
    # --- 2. ESTRATÉGIA DE ALTA: RSI Extremo (88%) ---
    if not np.isnan(current_rsi) and current_rsi > 75 and is_conf_put:
        strategy_used = "RSI Reversão (Sobrecompra + S/R) [attachment_1](attachment)"
        trend = "PUT"
        confidence = 88
        justification = f"REVERSÃO RÁPIDA (88%). RSI ({current_rsi:.2f}) em SOBRECOMPRA. CONFIRMAÇÃO: {conf_put_str}."
        return trend, justification, confidence, indicator_status, strategy_used

    if not np.isnan(current_rsi) and current_rsi < 25 and is_conf_call:
        strategy_used = "RSI Reversão (Sobrevenda + S/R)"
        trend = "CALL"
        confidence = 88
        justification = f"REVERSÃO RÁPIDA (88%). RSI ({current_rsi:.2f}) em SOBREVENDA. CONFIRMAÇÃO: {conf_call_str}."
        return trend, justification, confidence, indicator_status, strategy_used

    # --- 3. ESTRATÉGIA STOCHASTIC RÍGIDA (85%) ---
    if not np.isnan(current_stoch_k):
        # Stoch > 80 E Confirmação de Resistência
        if current_stoch_k > 80 and is_conf_put: 
            strategy_used = "Stoch RÍGIDO (Extremo com S/R) "
            trend = "PUT"
            confidence = 85
            justification = f"ALTA CONFIANÇA (85%). Stoch em SOBRECOMPRA (>80). Confirmação: {conf_put_str}."
            return trend, justification, confidence, indicator_status, strategy_used

        # Stoch < 20 E Confirmação de Suporte
        elif current_stoch_k < 20 and is_conf_call: 
            strategy_used = "Stoch RÍGIDO (Extremo com S/R)"
            trend = "CALL"
            confidence = 85
            justification = f"ALTA CONFIANÇA (85%). Stoch em SOBREVENDA (<20). Confirmação: {conf_call_str}."
            return trend, justification, confidence, indicator_status, strategy_used
        
        # --- 4. ESTRATÉGIA STOCHASTIC OPORTUNISTA (80%) ---
        if current_stoch_k > 80:
            strategy_used = "Stoch OPORTUNISTA (Reversão Pura)"
            trend = "PUT"
            confidence = 80
            justification = f"OPORTUNIDADE (80%). Stoch em SOBRECOMPRA (>80). Sem Confirmação S/R forte."
            return trend, justification, confidence, indicator_status, strategy_used

        elif current_stoch_k < 20:
            strategy_used = "Stoch OPORTUNISTA (Reversão Pura)"
            trend = "CALL"
            confidence = 80
            justification = f"OPORTUNIDADE (80%). Stoch em SOBREVENDA (<20). Sem Confirmação S/R forte."
            return trend, justification, confidence, indicator_status, strategy_used

    # --- 5. ESTRATÉGIA DE CURTO PRAZO (EMA Breakout - 70%) ---
    elif not np.isnan(current_ema):
        if current_close > current_ema:
            strategy_used = "Acompanhamento de Curto Prazo (EMA Breakout) "
            trend = "CALL"
            confidence = 70
            justification = f"Preço acima da EMA(10). Sem extremos ativos."

        elif current_close < current_ema:
            strategy_used = "Acompanhamento de Curto Prazo (EMA Breakout)"
            trend = "PUT"
            confidence = 70
            justification = f"Preço abaixo da EMA(10). Sem extremos ativos."
            
    return trend, justification, confidence, indicator_status, strategy_used


# --- FUNÇÕES FETCH E LÓGICA CORE ---

def fetch_macro_trend(ws, symbol):
    """
    Busca candles de 30m para determinar a tendência principal (MACRO) usando EMA(50).
    """
    MACRO_GRANULARITY = 1800 # 30 minutos
    
    macro_request = json.dumps({
        "ticks_history": symbol, "end": "latest", "count": 50, 
        "style": "candles", "granularity": MACRO_GRANULARITY 
    })
    ws.send(macro_request)
    
    response = json.loads(ws.recv())
    
    if response.get('error') or 'candles' not in response:
        add_log("AVISO: Falha ao obter dados MACRO (30m). Usando NEUTRA.")
        return "NEUTRA"

    df_macro = pd.DataFrame(response['candles'])
    df_macro = df_macro.rename(columns={'close': 'Close'}).astype(float) 
    
    df_macro['EMA_50'] = calculate_ema(df_macro['Close'], 50)
    
    if len(df_macro) < 50 or 'EMA_50' not in df_macro.columns or np.isnan(df_macro['EMA_50'].iloc[-1]):
        return "NEUTRA"

    current_close_macro = df_macro['Close'].iloc[-1]
    current_ema_macro = df_macro['EMA_50'].iloc[-1]

    if current_close_macro > current_ema_macro:
        return "CALL"
    elif current_close_macro < current_ema_macro:
        return "PUT"
    else:
        return "NEUTRA"


def fetch_candle_data(ws, symbol, granularity=300):
    """Solicita, analisa, determina a Tendência e a Estratégia (5m)."""
    
    granularity_minutes = granularity // 60 
    add_log(f"SOLICITANDO CANDLES de {granularity_minutes}m para análise de tendência...")
    
    candle_request = json.dumps({
        "ticks_history": symbol, "end": "latest", "count": 100, 
        "style": "candles", "granularity": granularity 
    })
    ws.send(candle_request)
    response = json.loads(ws.recv())
    
    if response.get('error'):
        error_msg = response['error'].get('message', 'Erro de API desconhecido')
        raise Exception(f"ERRO API (Candles): {error_msg}")

    if 'candles' not in response or len(response['candles']) < 20:
        raise Exception(f"AVISO: Dados de velas insuficientes para análise ({len(response.get('candles', []))} recebidos).")
    
    df = pd.DataFrame(response['candles'])
    df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}).astype(float)
    
    # --- CÁLCULO DE INDICADORES COM ATR ---
    df['EMA_10'] = calculate_ema(df['Close'], 10)
    df = calculate_stoch(df, 14, 3) 
    df = calculate_rsi(df, 14)        
    df = calculate_bbands(df, 20, 2)     
    df = calculate_atr(df, 14) # NOVO: Filtro de Volatilidade
    # -------------------------------------
    
    add_log(f"** DETECTOR DE CANDLES ** Recebidos {len(df)} velas de {symbol}.")
    
    trend, justification, confidence, indicator_status, strategy_used = strategy_selection_engine(
        df, granularity_minutes)
    
    return trend, justification, confidence, indicator_status, strategy_used

def monitor_ticks_and_signal(ws, symbol, trend, justification, confidence, indicator_status, strategy_used, granularity_minutes):
    """Monitoriza ticks e gera o Sinal Final (Timing)."""
    
    APROVEITAMENTO_JANELA_SEGUNDOS = 30 
    start_time = time.time()
    add_log(f"Tendência Confirmada: {trend} ({confidence}%). Janela de aproveitamento: {APROVEITAMENTO_JANELA_SEGUNDOS}s.")
    
    ws.send(json.dumps({"ticks": symbol, "subscribe": 1}))
    
    try:
        while BOT_STATUS == "ON":
            if time.time() - start_time > APROVEITAMENTO_JANELA_SEGUNDOS:
                add_log(f"AVISO: Janela de aproveitamento expirada. Sinal {trend} ignorado.")
                update_signal_data({
                    'direction': 'EXPIRADO', 'confidence': 0,
                    'justification': 'Sinal expirado (janela de 30s esgotada).'
                })
                break 
            
            message = ws.recv()
            data = json.loads(message)
            
            if data.get('tick'):
                tick = data['tick']
                
                entry_time_dt = datetime.utcfromtimestamp(tick['epoch'])
                exit_time_dt = entry_time_dt + timedelta(seconds=FIXED_TRADE_DURATION_SECONDS)
                
                update_signal_data({
                    'direction': trend, 
                    'trend': f"{trend.upper()} ({granularity_minutes}m)", 
                    'entry_time': entry_time_dt.strftime('%H:%M:%S'), 
                    'exit_time': exit_time_dt.strftime('%H:%M:%S'),
                    'confidence': confidence,
                    'indicator_status': indicator_status,
                    'justification': justification,
                    'strategy_used': strategy_used,
                    'tf': f'{granularity_minutes}m'
                })
                add_log(f"*** SINAL FINAL GERADO E APROVEITADO! *** {trend.upper()} ({confidence}%).")
                
                ws.send(json.dumps({"forget": tick['id']})) 
                break 

            time.sleep(0.1)

    except Exception as e:
        add_log(f"Erro na monitorização de ticks: {e}")
    finally:
        # Garante que a subscrição é limpa antes de fechar a conexão
        ws.send(json.dumps({"forget_all": "ticks"}))


def deriv_bot_core_logic(symbol, mode, api_token):
    """
    Loop principal que coordena a análise de velas e ticks.
    """
    global BOT_STATUS
    
    GRANULARITY_SECONDS = FIXED_TRADE_DURATION_SECONDS
    GRANULARITY_MINUTES = GRANULARITY_SECONDS // 60 
    
    add_log(f"Iniciando Bot. App ID: {MY_APP_ID}. Ativo: {symbol}, Modo: {mode}.")

    try:
        while BOT_STATUS == "ON":
            ws = None 
            try:
                # 1. CONEXÃO E AUTENTICAÇÃO
                ws = connect_ws(DERIV_URL, api_token) 
                add_log("Conexão estabelecida e autenticada para o ciclo de análise.")

                # --- FILTRO MACRO (30m) ---
                macro_trend = fetch_macro_trend(ws, symbol)
                add_log(f"** FILTRO MACRO ** Tendência 30m: {macro_trend}")
                # -------------------------

                # 2. ANÁLISE E SINAL (5m)
                trend, justification, confidence, indicator_status, strategy_used = fetch_candle_data(
                    ws, symbol, granularity=GRANULARITY_SECONDS) 
                
                # --- APLICAÇÃO DO FILTRO MTF PARA ASSERTIVIDADE ---
                final_trend = trend
                final_justification = justification
                final_confidence = confidence
                
                if trend != "NEUTRA":
                    if trend == macro_trend:
                        final_confidence = min(100, confidence + 10) # Bônus de 10%
                        final_justification += f" ** CONFIRMAÇÃO MACRO: Tendência 30m é {macro_trend}.**"
                        
                    elif trend != macro_trend and macro_trend != "NEUTRA":
                        # Só aceita sinais de altíssima confiança contra o macro (88%+ RSI/BBands)
                        if confidence < 88: 
                            final_trend = "NEUTRA"
                            final_confidence = 5
                            final_justification = f"FILTRADO: Sinal 5m ({trend}, {confidence}%) é CONTRA a Tendência MACRO 30m ({macro_trend})."
                # ------------------------------------------------------------
                
                if final_trend != "NEUTRA":
                    monitor_ticks_and_signal(ws, symbol, final_trend, final_justification, final_confidence, indicator_status, strategy_used, GRANULARITY_MINUTES)
                else:
                    update_signal_data({
                        'direction': 'NEUTRA', 'trend': f'NEUTRA ({GRANULARITY_MINUTES}m)', 
                        'confidence': final_confidence,
                        'strategy_used': strategy_used,
                        'justification': final_justification 
                    })
                    add_log(f"Tendência Neutra. Justificativa: {final_justification}. Aguardando a próxima análise...")
                
                # Pausa para o Próximo Ciclo (Obrigatório)
                time.sleep(90) 

            except Exception as e:
                add_log(f"ERRO NO CICLO: {e}")
                time.sleep(10) # Pausa menor em caso de erro
            finally:
                if ws:
                    ws.close() 
                    add_log("Conexão fechada para o próximo ciclo.")


    except Exception as e:
        add_log(f"ERRO FATAL (Global): {e}")
    finally:
        BOT_STATUS = "OFF"
        add_log("Bot Parado.")


# --- ROTAS FLASK PARA CONTROLO E INTERFACE ---

@app.route('/')
def index():
    # Esta rota espera que você tenha um arquivo 'index.html' na pasta 'templates'.
    # Se não tiver, pode usar o HTML que incluí nas respostas anteriores aqui.
    try:
        return render_template('index.html')
    except Exception:
        # Se você não tiver o arquivo, use o HTML embutido para testar.
        return """
        <!DOCTYPE html>
        <html lang="pt">
        <head>
            <meta charset="UTF-8">
            <title>Deriv Bot Core</title>
            <style>
                body { font-family: Arial, sans-serif; background-color: #1c1c1c; color: #f0f0f0; margin: 0; padding: 20px; }
                .container { max-width: 800px; margin: auto; background-color: #2c2c2c; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0, 0, 0, 0.5); }
                h1 { color: #4CAF50; text-align: center; }
                .controls { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; padding: 15px; border: 1px solid #3a3a3a; border-radius: 6px; }
                .controls label { display: block; margin-bottom: 5px; color: #aaa; }
                .controls input[type="text"], .controls select { width: 100%; padding: 10px; margin-bottom: 10px; border: 1px solid #555; border-radius: 4px; box-sizing: border-box; background-color: #333; color: #f0f0f0; }
                .controls button { padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; transition: background-color 0.3s; }
                #startBtn { background-color: #4CAF50; color: white; }
                #startBtn:hover { background-color: #45a049; }
                #stopBtn { background-color: #f44336; color: white; }
                #stopBtn:hover { background-color: #da190b; }
                #status-display { text-align: center; margin-top: 10px; font-size: 1.1em; padding: 10px; border-radius: 4px; }
                #log-area { max-height: 400px; overflow-y: scroll; background-color: #111; padding: 10px; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; font-size: 0.9em; border: 1px solid #3a3a3a; }
                .signal-info { margin-top: 15px; padding: 10px; border: 1px solid #4CAF50; border-radius: 4px; background-color: #333; }
                .signal-info p { margin: 5px 0; }
                .signal-label { font-weight: bold; color: #aaa; width: 150px; display: inline-block; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 Deriv Bot Core</h1>
                
                <div class="controls">
                    <div>
                        <label for="api_token">Token API (Deriv)</label>
                        <input type="text" id="api_token" placeholder="Insira seu Token API">
                    </div>
                    <div>
                        <label for="symbol">Ativo (Ex: R_100, VLT_100)</label>
                        <input type="text" id="symbol" value="R_100" placeholder="R_100">
                    </div>
                    <div>
                        <label for="mode">Modo de Operação</label>
                        <select id="mode">
                            <option value="demo">Demo (Virtual)</option>
                            <option value="real">Real</option>
                        </select>
                    </div>
                    <div>
                        <button id="startBtn">INICIAR BOT</button>
                        <button id="stopBtn">PARAR BOT</button>
                        <div id="status-display">Status: OFF</div>
                    </div>
                </div>

                <h2>Sinal Atual</h2>
                <div class="signal-info" id="signal-display">Aguardando análise inicial...</div>

                <h2>Logs de Atividade</h2>
                <div id="log-area">Aguardando logs...</div>
            </div>

            <script>
                let statusElement = document.getElementById('status-display');
                let logArea = document.getElementById('log-area');
                let signalDisplay = document.getElementById('signal-display');
                let isPolling = false;

                function updateStatus(newStatus, message) {
                    statusElement.textContent = `Status: ${newStatus}`;
                    if (newStatus === 'ON') {
                        statusElement.style.backgroundColor = '#2ecc71';
                    } else {
                        statusElement.style.backgroundColor = '#e74c3c';
                    }
                    if (message) { addLog(message); }
                }

                function addLog(message) {
                    const logEntry = document.createElement('div');
                    logEntry.className = 'log-entry';
                    logEntry.textContent = message;
                    logArea.prepend(logEntry); 
                    while (logArea.children.length > 100) { logArea.removeChild(logArea.lastChild); }
                }

                function renderSignal(data) {
                    signalDisplay.innerHTML = `
                        <p><span class="signal-label">Direção:</span> <strong>${data.direction}</strong></p>
                        <p><span class="signal-label">Confiança:</span> ${data.confidence}%</p>
                        <p><span class="signal-label">Estratégia:</span> ${data.strategy_used}</p>
                        <p><span class="signal-label">Justificativa:</span> ${data.justification}</p>
                        <p><span class="signal-label">Status Indicadores:</span> ${data.indicator_status}</p>
                        <p><span class="signal-label">Entrada (UTC):</span> ${data.entry_time}</p>
                    `;
                }

                function pollStatusAndLogs() {
                    if (!isPolling) return;
                    
                    fetch('/status')
                        .then(response => response.json())
                        .then(data => {
                            updateStatus(data.status);
                            renderSignal(data.signal_data);
                            logArea.innerHTML = ''; 
                            data.logs.slice().reverse().forEach(log => { // Logs vêm do mais antigo ao mais recente
                                const logEntry = document.createElement('div');
                                logEntry.className = 'log-entry';
                                logEntry.textContent = log;
                                logArea.appendChild(logEntry);
                            });
                        })
                        .catch(error => console.error('Erro ao buscar status:', error));

                    setTimeout(pollStatusAndLogs, 1000); 
                }

                document.getElementById('startBtn').addEventListener('click', () => {
                    const api_token = document.getElementById('api_token').value.trim();
                    const symbol = document.getElementById('symbol').value.trim();
                    const mode = document.getElementById('mode').value;

                    if (!api_token || !symbol) { alert("Por favor, preencha o Token API e o Ativo."); return; }

                    fetch('/control', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ action: 'start', symbol: symbol, mode: mode, api_token: api_token })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status !== 'ERROR') {
                            updateStatus(data.status, data.message);
                            isPolling = true;
                            pollStatusAndLogs(); 
                        } else {
                            updateStatus('OFF', data.message);
                        }
                    })
                    .catch(error => {
                        console.error('Erro ao iniciar:', error);
                        updateStatus('OFF', 'Erro de conexão ao iniciar.');
                    });
                });

                document.getElementById('stopBtn').addEventListener('click', () => {
                    fetch('/control', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ action: 'stop' })
                    })
                    .then(response => response.json())
                    .then(data => {
                        updateStatus('OFF', data.message);
                        isPolling = false;
                    });
                });

                fetch('/status')
                    .then(response => response.json())
                    .then(data => {
                        updateStatus(data.status);
                        renderSignal(data.signal_data);
                        if (data.status === 'ON') {
                            isPolling = true;
                            pollStatusAndLogs();
                        }
                    });
            </script>
        </body>
        </html>
        """

@app.route('/control', methods=['POST'])
def control_bot():
    global BOT_STATUS, BOT_THREAD, LOG_MESSAGES, CURRENT_SYMBOL
    
    action = request.json.get('action')
    symbol = request.json.get('symbol')
    mode = request.json.get('mode')
    api_token = request.json.get('api_token')

    if action == 'start' and BOT_STATUS != "ON":
        LOG_MESSAGES = [] 
        update_signal_data({'direction': 'AGUARDANDO', 'entry_time': '--:--:--', 'exit_time': '--:--:--', 'confidence': 0, 'indicator_status': 'A iniciar...', 'justification': 'Aguardando autenticação do token.'})
        
        if not api_token:
            return jsonify({'status': 'ERROR', 'message': 'Token API não fornecido.'}), 400
        
        # Simples check de validade do token
        if len(api_token.strip()) < 10: 
            return jsonify({'status': 'ERROR', 'message': 'Token API inválido (muito curto).'}), 400
            
        BOT_STATUS = "ON"
        CURRENT_SYMBOL = symbol # CORRIGIDO: Guarda o ativo escolhido
        
        BOT_THREAD = threading.Thread(target=deriv_bot_core_logic, args=(symbol, mode, api_token))
        BOT_THREAD.start()
        
        return jsonify({'status': 'ON', 'message': f'Bot iniciado em modo {mode} no {symbol}.'}), 200

    elif action == 'stop' and BOT_STATUS == "ON":
        BOT_STATUS = "OFF"
        update_signal_data({'direction': 'OFF', 'entry_time': '--:--:--', 'exit_time': '--:--:--', 'confidence': 0, 'indicator_status': 'Desligado', 'justification': 'O bot foi parado pelo utilizador.', 'strategy_used': 'Nenhuma'})
        return jsonify({'status': 'OFF', 'message': 'Comando de Paragem enviado.'}), 200
        
    return jsonify({'status': BOT_STATUS, 'message': 'Comando não executado ou estado inválido.'}), 200

@app.route('/status')
def get_status():
    global LOG_MESSAGES, BOT_STATUS, FINAL_SIGNAL_DATA, CURRENT_SYMBOL
    
    return jsonify({
        'status': BOT_STATUS, 
        'logs': LOG_MESSAGES, 
        'signal_data': FINAL_SIGNAL_DATA,
        'current_symbol': CURRENT_SYMBOL
    }), 200

if __name__ == '__main__':
    # Usado para rodar no Render (BIND)
    try:
        # Pega a porta da variável de ambiente do Render
        port = int(os.environ.get('PORT', 5000))
        # Usa make_server para garantir que o Flask funciona corretamente no Render
        http_server = make_server('0.0.0.0', port, app)
        add_log(f"Servidor Flask iniciado na porta {port}")
        
        # Inicia o servidor e bloqueia
        http_server.serve_forever()
        
    except Exception as e:
        add_log(f"ERRO DE INICIALIZAÇÃO DO SERVIDOR: {e}")

