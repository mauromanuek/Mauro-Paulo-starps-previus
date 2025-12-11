import os
import threading
import json
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from websocket import create_connection
import pandas as pd
import numpy as np

# --- CONFIGURAÇÕES DE APLICAÇÃO ---
MY_APP_ID = 114910 
FIXED_TRADE_DURATION_SECONDS = 300 # 5 minutos
MAX_LOG_SIZE = 50 
S_R_LOOKBACK = 20 # Velas para identificar Suporte/Resistência

# --- VARIÁVEIS GLOBAIS DE ESTADO ---
app = Flask(__name__)
BOT_STATUS = "OFF"
BOT_THREAD = None
LOG_MESSAGES = [] 

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
    """Cria e autentica a conexão WebSocket usando o token fornecido pelo frontend."""
    ws = create_connection(url)
    cleaned_token = api_token.strip() 
    ws.send(json.dumps({"authorize": cleaned_token})) 
    auth_response = json.loads(ws.recv())
    
    if auth_response.get('error'):
        raise Exception(f"Erro de Autenticação: {auth_response['error']['message']}")
    
    return ws

# --- CÁLCULO DE INDICADORES NATIVO (100% ROBUSTO) ---

def calculate_ema(series, length):
    """Calcula a Média Móvel Exponencial (EMA) de forma nativa."""
    return series.ewm(span=length, adjust=False).mean()

def calculate_rsi(df, length=14):
    """Calcula o Índice de Força Relativa (RSI) de forma nativa."""
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Cálculos de média móvel exponencial para o RSI
    avg_gain = gain.ewm(com=length - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=length - 1, adjust=False).mean()
    
    # Evita divisão por zero
    rs = avg_gain / avg_loss.replace(0, np.nan) 
    rsi = 100 - (100 / (1 + rs))
    df[f'RSI_{length}'] = rsi
    return df

def calculate_bbands(df, length=20, std_dev=2):
    """Calcula as Bandas de Bollinger (BBands) de forma nativa."""
    df[f'SMA_{length}'] = df['Close'].rolling(window=length).mean()
    df[f'StdDev_{length}'] = df['Close'].rolling(window=length).std()
    
    df[f'BBU_{length}_{std_dev}.0'] = df[f'SMA_{length}'] + (df[f'StdDev_{length}'] * std_dev)
    df[f'BBL_{length}_{std_dev}.0'] = df[f'SMA_{length}'] - (df[f'StdDev_{length}'] * std_dev)
    
    return df

def calculate_stoch(df, k_length=14, d_length=3):
    """Calcula o Stochastic Oscillator de forma nativa."""
    low_min = df['Low'].rolling(window=k_length).min()
    high_max = df['High'].rolling(window=k_length).max()
    
    # Previne divisão por zero, caso high_max == low_min
    range_diff = high_max - low_min
    range_diff.replace(0, np.nan, inplace=True) 
    
    df['%K'] = 100 * (df['Close'] - low_min) / range_diff
    df[f'STOCHk_{k_length}_{d_length}_{d_length}'] = df['%K'].rolling(window=d_length).mean() 
    return df

# --- LÓGICA DE DETECÇÃO DE CANDLESTICK (Mantida) ---

def detect_candlestick_pattern(df):
    """
    Detecta os padrões de candlestick de reversão usando a lógica OHLC. 
    Retorna 100 para Bullish Forte, -100 para Bearish Forte, 0 caso contrário.
    """
    
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
    
    is_bear_engulf = (c['Close'] < c['Open']) and (p['Close'] > p['Open']) and \
                     (c['Open'] > p['Close']) and (c['Close'] < p['Open']) and \
                     (body_c > range_p)

    is_bull_engulf = (c['Close'] > c['Open']) and (p['Close'] < p['Open']) and \
                     (c['Open'] < p['Close']) and (c['Close'] > p['Open']) and \
                     (body_c > range_p)

    if is_bear_engulf: return -100
    if is_bull_engulf: return 100

    return 0 

# --- ESTRATÉGIA: CONFIRMAÇÃO DE PADRÕES E S/R (Mantida) ---

def check_confirmation(df, current_close):
    """Verifica padrões de candlestick de reversão e proximidade de S/R."""
    
    recent_high = df['High'].iloc[-S_R_LOOKBACK:].max()
    recent_low = df['Low'].iloc[-S_R_LOOKBACK:].min()
    
    SR_TOLERANCE = 0.0005 
    is_near_resistance = (recent_high - current_close) / recent_high < SR_TOLERANCE
    is_near_support = (current_close - recent_low) / recent_low < SR_TOLERANCE

    pattern_val = detect_candlestick_pattern(df) 
    is_bullish_pattern = (pattern_val > 0)
    is_bearish_pattern = (pattern_val < 0)
            
    confirmation_bullish, confirmation_bearish = "", ""
    
    if is_near_support and is_bullish_pattern:
        confirmation_bullish = "Forte: Candlestick Bullish (Reversão) na Zona de Suporte."
    elif is_near_support:
        confirmation_bullish = "Suporte: Preço na Zona de Suporte Recente."
        
    if is_near_resistance and is_bearish_pattern:
        confirmation_bearish = "Forte: Candlestick Bearish (Reversão) na Zona de Resistência."
    elif is_near_resistance:
        confirmation_bearish = "Resistência: Preço na Zona de Resistência Recente."

    return confirmation_bullish, confirmation_bearish, recent_low, recent_high

# --- ESTRATÉGIA: MOTOR DE SELEÇÃO E DECISÃO (Reajustado sem ADX) ---

def strategy_selection_engine(df, granularity_minutes):
    """
    Analisa o contexto e escolhe a estratégia. Prioridade: BBands > RSI > Stochastic/EMA.
    """
    
    # 1. Obter valores recentes
    current_close = df['Close'].iloc[-1]
    current_ema = df['EMA_10'].iloc[-1]
    current_stoch_k = df['STOCHk_14_3_3'].iloc[-1]
    
    current_rsi = df['RSI_14'].iloc[-1]
    bbands_upper = df['BBU_20_2.0'].iloc[-1]
    bbands_lower = df['BBL_20_2.0'].iloc[-1]
    
    conf_call, conf_put, recent_low, recent_high = check_confirmation(df, current_close)
    
    # Status dos Indicadores
    ema_status = f"{current_ema:.4f}" if not np.isnan(current_ema) else "--"
    rsi_status = f"{current_rsi:.2f}" if not np.isnan(current_rsi) else "--"
    
    indicator_status = f"EMA(10): {ema_status}, Stoch K: {current_stoch_k:.2f}, RSI: {rsi_status}" 
    
    trend, confidence, strategy_used = "NEUTRA", 40, "Análise de Contexto"
    justification = "Mercado Neutro ou sem sinais de alta confiança."

    # --- 1. ESTRATÉGIA DE ALTA PRIORIDADE: BANDAS DE BOLLINGER (90%) ---
    # Só executa se o valor não for NaN (ou seja, se o cálculo foi bem sucedido)
    if not np.isnan(bbands_upper) and current_close > bbands_upper:
        strategy_used = "BBANDS Reversão (Sobre-extensão)"
        trend = "PUT"
        confidence = 90
        justification = f"REVERSÃO FORTE. Preço ({current_close:.4f}) acima da Banda Superior de Bollinger ({bbands_upper:.4f})."
        return trend, justification, confidence, indicator_status, strategy_used

    if not np.isnan(bbands_lower) and current_close < bbands_lower:
        strategy_used = "BBANDS Reversão (Sobre-extensão)"
        trend = "CALL"
        confidence = 90
        justification = f"REVERSÃO FORTE. Preço ({current_close:.4f}) abaixo da Banda Inferior de Bollinger ({bbands_lower:.4f})."
        return trend, justification, confidence, indicator_status, strategy_used
        
    # --- 2. ESTRATÉGIA DE ALTA PRIORIDADE: RSI (88%) ---
    if not np.isnan(current_rsi) and current_rsi > 70 and conf_put:
        strategy_used = "RSI Reversão (Sobrecompra)"
        trend = "PUT"
        confidence = 88
        justification = f"REVERSÃO RÁPIDA. RSI em SOBRECOMPRA (>70). CONFIRMAÇÃO: {conf_put}."
        return trend, justification, confidence, indicator_status, strategy_used

    if not np.isnan(current_rsi) and current_rsi < 30 and conf_call:
        strategy_used = "RSI Reversão (Sobrevenda)"
        trend = "CALL"
        confidence = 88
        justification = f"REVERSÃO RÁPIDA. RSI em SOBREVENDA (<30). CONFIRMAÇÃO: {conf_call}."
        return trend, justification, confidence, indicator_status, strategy_used

    # --- 3. ESTRATÉGIA DE REVERSÃO / TENDÊNCIA SECUNDÁRIA (Stochastic/EMA, 85%) ---
    
    # Stochastic (Reversão de Extremos)
    if not np.isnan(current_stoch_k):
        if current_stoch_k > 80 and conf_put:
            strategy_used = "Reversão de Extremos (Stochastic Oscillator)"
            trend = "PUT"
            confidence = 85
            justification = f"Stochastic em SOBRECOMPRA (>80). CONFIRMAÇÃO: {conf_put}."

        elif current_stoch_k < 20 and conf_call:
            strategy_used = "Reversão de Extremos (Stochastic Oscillator)"
            trend = "CALL"
            confidence = 85
            justification = f"Stochastic em SOBREVENDA (<20). CONFIRMAÇÃO: {conf_call}."
            
    # EMA Breakout (Tendência de Curto Prazo)
    elif not np.isnan(current_ema):
        if current_close > current_ema:
            strategy_used = "Acompanhamento de Curto Prazo (EMA Breakout)"
            trend = "CALL"
            confidence = 70
            justification = f"Preço acima da EMA(10). Confirmação: {conf_call if conf_call else 'Nenhuma'}"

        elif current_close < current_ema:
            strategy_used = "Acompanhamento de Curto Prazo (EMA Breakout)"
            trend = "PUT"
            confidence = 70
            justification = f"Preço abaixo da EMA(10). Confirmação: {conf_put if conf_put else 'Nenhuma'}"
            
    return trend, justification, confidence, indicator_status, strategy_used


# --- FUNÇÕES FETCH (Mantidas com os novos cálculos) ---

def fetch_macro_trend(ws, symbol):
    """
    Busca candles de 30m para determinar a tendência principal (MACRO) usando EMA(50) nativo.
    """
    MACRO_GRANULARITY = 1800 # 30 minutos
    
    macro_request = json.dumps({
        "ticks_history": symbol, "end": "latest", "count": 50, 
        "style": "candles", "granularity": MACRO_GRANULARITY 
    })
    ws.send(macro_request)
    
    response = json.loads(ws.recv())
    
    if response.get('error') or 'candles' not in response:
        add_log("AVISO: Falha ao obter dados MACRO (30m).")
        return "NEUTRA"

    df_macro = pd.DataFrame(response['candles'])
    df_macro = df_macro.rename(columns={'close': 'Close'}).astype(float) 
    
    # Calcular EMA 50 nativa
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
    """Solicita, analisa, determina a Tendência e a Estratégia (5m) - AGORA 100% ROBUSTO."""
    
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
        add_log(f"ERRO API (Candles): {error_msg}")
        return "NEUTRA", 0, "Erro de API ao buscar velas", "EMA: --", "Erro de API" 

    if 'candles' not in response or (response.get('msg_type') != 'history' and response.get('msg_type') != 'candles'):
        add_log(f"AVISO: Resposta de velas inesperada. Tipo de mensagem: {response.get('msg_type')}. Pulando análise.")
        return "NEUTRA", 0, "Resposta de velas incompleta", "EMA: --", "Falha de Dados" 
    
    add_log(f"** DETECTOR DE CANDLES ** Recebidos {len(response['candles'])} velas de {symbol}.")
    
    df = pd.DataFrame(response['candles'])
    df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}).astype(float)
    
    # --- CÁLCULO DE INDICADORES NATIVOS (100% ROBUSTO) ---
    df['EMA_10'] = calculate_ema(df['Close'], 10)
    # ADX REMOVIDO PARA EVITAR ERROS DE BIBLIOTECA
    df = calculate_stoch(df, 14, 3) 
    df = calculate_rsi(df, 14)        
    df = calculate_bbands(df, 20, 2)     
    # -----------------------------------------------------
    
    trend, justification, confidence, indicator_status, strategy_used = strategy_selection_engine(
        df, granularity_minutes)
    
    return trend, justification, confidence, indicator_status, strategy_used

def monitor_ticks_and_signal(ws, symbol, trend, justification, confidence, indicator_status, strategy_used, granularity_minutes):
    """Monitoriza ticks e gera o Sinal Final (Timing)."""
    
    add_log(f"Tendência Confirmada: {trend} usando {strategy_used}. Monitorizando ticks...")
    
    ws.send(json.dumps({"ticks": symbol, "subscribe": 1}))
    
    try:
        while BOT_STATUS == "ON":
            message = ws.recv()
            data = json.loads(message)
            
            if data.get('tick'):
                tick = data['tick']
                add_log(f"** DETECTOR DE TICKS ** Preço {symbol}: {float(tick['quote'])}")

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
                add_log(f"*** SINAL FINAL GERADO! *** {trend.upper()} via {strategy_used}.")
                
                ws.send(json.dumps({"forget": tick['id']})) 
                break 

            time.sleep(0.1)

    except Exception as e:
        add_log(f"Erro na monitorização de ticks: {e}")
    finally:
        ws.send(json.dumps({"forget_all": "ticks"}))


def deriv_bot_core_logic(symbol, mode, api_token):
    """
    Loop principal que coordena a análise de velas e ticks.
    Inclui Filtro Multi-Timeframe (MTF) para aumentar a assertividade.
    """
    global BOT_STATUS
    
    GRANULARITY_SECONDS = FIXED_TRADE_DURATION_SECONDS
    GRANULARITY_MINUTES = GRANULARITY_SECONDS // 60 
    
    WS_URL_DERIV = f"wss://ws.derivws.com/websockets/v3?app_id={MY_APP_ID}"
    WS_URL = WS_URL_DERIV 
    
    add_log(f"Iniciando Bot. App ID: {MY_APP_ID}. Ativo: {symbol}, Modo: {mode}.")

    try:
        while BOT_STATUS == "ON":
            ws = None 
            try:
                # 1. CONEXÃO E AUTENTICAÇÃO LIMPA EM CADA CICLO
                ws = connect_ws(WS_URL, api_token) 
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
                
                if trend == macro_trend and trend != "NEUTRA":
                    final_confidence = min(100, confidence + 15)
                    final_justification += f" ** CONFIRMAÇÃO MACRO: Tendência 30m é {macro_trend}.**"
                    
                elif trend != macro_trend and trend != "NEUTRA" and macro_trend != "NEUTRA":
                    final_trend = "NEUTRA"
                    final_confidence = 5
                    final_justification = f"FILTRADO: Sinal 5m ({trend}) é CONTRA a Tendência MACRO 30m ({macro_trend})."
                # ------------------------------------------------------------
                
                if final_trend != "NEUTRA":
                    monitor_ticks_and_signal(ws, symbol, final_trend, final_justification, final_confidence, indicator_status, strategy_used, GRANULARITY_MINUTES)
                else:
                    update_signal_data({
                        'direction': 'NEUTRA', 
                        'trend': f'NEUTRA ({GRANULARITY_MINUTES}m)', 
                        'confidence': final_confidence,
                        'strategy_used': strategy_used,
                        'justification': final_justification 
                    })
                    add_log(f"Tendência Neutra. Justificativa: {final_justification}. Aguardando a próxima análise...")
                
                time.sleep(30) 

            except Exception as e:
                add_log(f"ERRO NO CICLO: {e}")
                time.sleep(10) 
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
    return render_template('index.html')

@app.route('/control', methods=['POST'])
def control_bot():
    """Recebe o comando INICIAR/PARAR e o Token do frontend."""
    global BOT_STATUS, BOT_THREAD, LOG_MESSAGES
    
    action = request.json.get('action')
    symbol = request.json.get('symbol')
    mode = request.json.get('mode')
    api_token = request.json.get('api_token') 

    if action == 'start' and BOT_STATUS != "ON":
        LOG_MESSAGES = [] 
        update_signal_data({'direction': 'AGUARDANDO', 'entry_time': '--:--:--', 'exit_time': '--:--:--', 'confidence': 0, 'indicator_status': 'A iniciar...', 'justification': 'Aguardando autenticação do token.'})
        
        if not api_token:
            return jsonify({'status': 'ERROR', 'message': 'Token API não fornecido.'}), 400
            
        BOT_STATUS = "ON"
        
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
    global LOG_MESSAGES, BOT_STATUS, FINAL_SIGNAL_DATA
    
    return jsonify({
        'status': BOT_STATUS, 
        'logs': LOG_MESSAGES, 
        'signal_data': FINAL_SIGNAL_DATA 
    }), 200

if __name__ == '__main__':
    add_log("Servidor Flask inicializado. (Lembre-se de usar Gunicorn no Render!)")
    app.run(debug=True, use_reloader=False)
