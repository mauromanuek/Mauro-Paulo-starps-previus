import os
import threading
import json
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from websocket import create_connection
import pandas as pd
import pandas_ta as ta
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
    'indicator_status': 'ADX: --, EMA: --, Stoch: --',
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
    
    ws.send(json.dumps({"authorize": api_token})) 
    auth_response = json.loads(ws.recv())
    
    if auth_response.get('error'):
        raise Exception(f"Erro de Autenticação: {auth_response['error']['message']}")
    
    return ws

# --- LÓGICA DE DETECÇÃO DE CANDLESTICK (DETECÇÃO INTERNA) ---

def detect_candlestick_pattern(df):
    """
    Detecta os padrões de candlestick de reversão (Martelo, Estrela Cadente e Engolfo) 
    usando a lógica OHLC. 
    Retorna 100 para Bullish Forte, -100 para Bearish Forte, 0 caso contrário.
    """
    
    if len(df) < 2:
        return 0
        
    c = df.iloc[-1] # Vela Atual (Current)
    p = df.iloc[-2] # Vela Anterior (Previous)
    
    range_c = c['High'] - c['Low']
    body_c = abs(c['Close'] - c['Open'])

    if range_c == 0 or range_c < 0.00001:
        return 0

    is_small_body = body_c < 0.3 * range_c
    
    # --- 1. MARTELO (BULLISH HAMMER) ---
    lower_shadow_c = min(c['Open'], c['Close']) - c['Low']
    is_hammer = is_small_body and (lower_shadow_c > 2 * body_c)

    if is_hammer:
        return 100 

    # --- 2. ESTRELA CADENTE (BEARISH SHOOTING STAR) ---
    upper_shadow_c = c['High'] - max(c['Open'], c['Close'])
    is_shooting_star = is_small_body and (upper_shadow_c > 2 * body_c)

    if is_shooting_star:
        return -100 

    # --- 3. ENGOLFO (BULLISH/BEARISH ENGULFING) ---
    range_p = p['High'] - p['Low']
    
    # Engolfo de Baixa (Bearish Engulfing): Vela vermelha que engole a verde anterior
    is_bear_engulf = (c['Close'] < c['Open']) and (p['Close'] > p['Open']) and \
                     (c['Open'] > p['Close']) and (c['Close'] < p['Open']) and \
                     (body_c > range_p)

    # Engolfo de Alta (Bullish Engulfing): Vela verde que engole a vermelha anterior
    is_bull_engulf = (c['Close'] > c['Open']) and (p['Close'] < p['Open']) and \
                     (c['Open'] < p['Close']) and (c['Close'] > p['Open']) and \
                     (body_c > range_p)

    if is_bear_engulf:
        return -100
    if is_bull_engulf:
        return 100

    return 0 

# --- ESTRATÉGIA: CONFIRMAÇÃO DE PADRÕES E S/R ---

def check_confirmation(df, current_close):
    """
    Verifica se há padrões de candlestick de reversão E se o preço está próximo 
    de um Suporte ou Resistência recente.
    """
    
    # 1. Identificação Simples de S/R (Max/Min)
    recent_high = df['High'].iloc[-S_R_LOOKBACK:].max()
    recent_low = df['Low'].iloc[-S_R_LOOKBACK:].min()
    
    SR_TOLERANCE = 0.0005 
    is_near_resistance = (recent_high - current_close) / recent_high < SR_TOLERANCE
    is_near_support = (current_close - recent_low) / recent_low < SR_TOLERANCE

    # 2. Detecção de Padrões de Candlestick (Detecção Interna)
    pattern_val = detect_candlestick_pattern(df) 

    is_bullish_pattern = (pattern_val > 0)
    is_bearish_pattern = (pattern_val < 0)
            
    # 3. Formação da Justificativa
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

# --- ESTRATÉGIA: MOTOR DE SELEÇÃO E DECISÃO ---

def strategy_selection_engine(df, granularity_minutes):
    """
    Analisa o contexto (ADX), escolhe a estratégia e busca confirmação S/R/Candle.
    """
    # 1. Obter valores recentes
    current_adx = df['ADX_14'].iloc[-1]
    current_close = df['Close'].iloc[-1]
    current_ema = df['EMA_10'].iloc[-1]
    current_stoch_k = df['STOCHk_14_3_3'].iloc[-1]
    
    # Obter Confirmação de S/R e Padrões
    conf_call, conf_put, recent_low, recent_high = check_confirmation(df, current_close)
    
    # Status dos Indicadores
    indicator_status = f"ADX: {current_adx:.2f}, EMA(10): {current_ema:.4f}, Stoch K: {current_stoch_k:.2f}"
    
    # Preparação da Decisão
    trend, confidence, strategy_used = "NEUTRA", 40, "Análise de Contexto"
    justification = "O mercado está em consolidação e sem sinais claros de extremos. Aguardando novo contexto."

    # --- DECISÃO DE CONTEXTO ---
    
    if current_adx > 30: # Tendência Forte (Trend-Following)
        strategy_used = "Acompanhamento de Tendência (EMA Breakout)"
        
        if current_close > current_ema and df['Close'].iloc[-2] > df['EMA_10'].iloc[-2]:
            trend = "CALL"
            confidence = 75
            justification = f"TENDÊNCIA FORTE (ADX {current_adx:.2f}). O Preço está acima da EMA (10), indicando continuidade de ALTA. CONFIRMAÇÃO: {conf_call if conf_call else 'Nenhuma'}"
            if conf_call: confidence += 10

        elif current_close < current_ema and df['Close'].iloc[-2] < df['EMA_10'].iloc[-2]:
            trend = "PUT"
            confidence = 75
            justification = f"TENDÊNCIA FORTE (ADX {current_adx:.2f}). O Preço está abaixo da EMA (10), indicando continuidade de BAIXA. CONFIRMAÇÃO: {conf_put if conf_put else 'Nenhuma'}"
            if conf_put: confidence += 10

    elif current_adx < 25: # Consolidação (Reversão de Extremos)
        strategy_used = "Reversão de Extremos (Stochastic Oscillator)"

        if current_stoch_k > 80 and conf_put:
            trend = "PUT"
            confidence = 85
            justification = f"CONSOLIDAÇÃO (ADX {current_adx:.2f}). O Stochastic está em SOBRECOMPRA (>80). CONFIRMAÇÃO: {conf_put} - indicando reversão iminente."

        elif current_stoch_k < 20 and conf_call:
            trend = "CALL"
            confidence = 85
            justification = f"CONSOLIDAÇÃO (ADX {current_adx:.2f}). O Stochastic está em SOBREVENDA (<20). CONFIRMAÇÃO: {conf_call} - indicando reversão iminente."
        
    return trend, justification, confidence, indicator_status, strategy_used

def fetch_candle_data(ws, symbol, granularity=300):
    """Solicita, analisa (EMA/ADX/Stoch), determina a Tendência e a Estratégia."""
    add_log(f"SOLICITANDO CANDLES de {granularity//60}m para análise de tendência...")
    
    candle_request = json.dumps({
        "ticks_history": symbol, "end": "latest", "count": 100, 
        "style": "candles", "granularity": granularity 
    })
    ws.send(candle_request)
    response = json.loads(ws.recv())
    
    # 1. VERIFICAÇÃO DE ERRO DA API
    if response.get('error'):
        error_msg = response['error'].get('message', 'Erro de API desconhecido')
        add_log(f"ERRO API (Candles): {error_msg}")
        return "NEUTRA", 0, "Erro de API ao buscar velas", "ADX: --", "Erro de API" 

    # 2. VERIFICAÇÃO ROBUSTA DA CHAVE 'CANDLES' (Correção do KeyError: 'candles')
    if response.get('msg_type') != 'history' or 'candles' not in response:
        add_log(f"AVISO: Resposta de velas inesperada. Tipo de mensagem: {response.get('msg_type')}. Pulando análise de velas.")
        return "NEUTRA", 0, "Resposta de velas incompleta", "ADX: --", "Falha de Dados" 

    
    add_log(f"** DETECTOR DE CANDLES ** Recebidos {len(response['candles'])} velas de {symbol}.")
    
    df = pd.DataFrame(response['candles'])
    df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}).astype(float)
    
    # Cálculo de Indicadores Múltiplos
    df.ta.ema(length=10, append=True)
    df.ta.adx(length=14, append=True)
    df.ta.stoch(k=14, d=3, append=True)
    
    # A detecção de Candlestick é feita em 'check_confirmation'
    
    trend, justification, confidence, indicator_status, strategy_used = strategy_selection_engine(
        df, granularity // 60)
    
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
    """Loop principal que coordena a análise de velas e ticks, recebendo o token."""
    global BOT_STATUS
    
    GRANULARITY_SECONDS = FIXED_TRADE_DURATION_SECONDS
    GRANULARITY_MINUTES = GRANULARITY_SECONDS // 60
    
    # URLs da API
    WS_URL_BASE = f"wss://ws.binaryws.com/websockets/v3?app_id={MY_APP_ID}"
    WS_URL_DERIV = f"wss://ws.derivws.com/websockets/v3?app_id={MY_APP_ID}"
    
    # Usa o URL de Deriv (mais comum para tokens) ou Binary (para modo demo)
    WS_URL = WS_URL_DERIV if mode == 'real' else WS_URL_BASE # Mantemos a distinção para flexibilidade
    
    add_log(f"Iniciando Bot. App ID: {MY_APP_ID}. Ativo: {symbol}, Modo: {mode}.")

    try:
        ws = connect_ws(WS_URL, api_token) # Autentica
        add_log("Autenticação e Conexão estabelecidas com a Deriv.")

        while BOT_STATUS == "ON":
            trend, justification, confidence, indicator_status, strategy_used = fetch_candle_data(
                ws, symbol, granularity=GRANULARITY_SECONDS) 
            
            if trend != "NEUTRA":
                monitor_ticks_and_signal(ws, symbol, trend, justification, confidence, indicator_status, strategy_used, GRANULARITY_MINUTES)
            else:
                update_signal_data({
                    'direction': 'NEUTRA', 
                    'trend': f'NEUTRA ({granularity_minutes}m)', 
                    'confidence': 30,
                    'strategy_used': strategy_used,
                    'justification': justification 
                })
                add_log("Tendência Neutra. Aguardando a próxima análise...")
                
            time.sleep(30) 

    except Exception as e:
        add_log(f"ERRO FATAL: {e}")
    finally:
        if 'ws' in locals():
            ws.close()
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
