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
    
    cleaned_token = api_token.strip() 
    
    ws.send(json.dumps({"authorize": cleaned_token})) 
    auth_response = json.loads(ws.recv())
    
    if auth_response.get('error'):
        raise Exception(f"Erro de Autenticação: {auth_response['error']['message']}")
    
    return ws

# --- LÓGICA DE DETECÇÃO DE CANDLESTICK ---

def detect_candlestick_pattern(df):
    """
    Detecta os padrões de candlestick de reversão (Martelo, Estrela Cadente e Engolfo) 
    usando a lógica OHLC. 
    Retorna 100 para Bullish Forte, -100 para Bearish Forte, 0 caso contrário.
    """
    
    if len(df) < 2: return 0
        
    c = df.iloc[-1] 
    p = df.iloc[-2] 
    
    range_c = c['High'] - c['Low']
    body_c = abs(c['Close'] - c['Open'])

    if range_c == 0 or range_c < 0.00001: return 0

    is_small_body = body_c < 0.3 * range_c
    
    # --- 1. MARTELO (BULLISH HAMMER) ---
    lower_shadow_c = min(c['Open'], c['Close']) - c['Low']
    is_hammer = is_small_body and (lower_shadow_c > 2 * body_c)
    if is_hammer: return 100 

    # --- 2. ESTRELA CADENTE (BEARISH SHOOTING STAR) ---
    upper_shadow_c = c['High'] - max(c['Open'], c['Close'])
    is_shooting_star = is_small_body and (upper_shadow_c > 2 * body_c)
    if is_shooting_star: return -100 

    # --- 3. ENGOLFO (BULLISH/BEARISH ENGULFING) ---
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

# --- ESTRATÉGIA: CONFIRMAÇÃO DE PADRÕES E S/R ---

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

# --- ESTRATÉGIA: MOTOR DE SELEÇÃO E DECISÃO ---

def strategy_selection_engine(df, granularity_minutes):
    """
    Analisa o contexto (ADX), escolhe a estratégia e busca confirmação S/R/Candle.
    PRIORIDADE: BBands > RSI > Stochastic > ADX/EMA
    """
    
    # 1. Obter valores recentes
    current_adx = df['ADX_14'].iloc[-1]
    current_close = df['Close'].iloc[-1]
    current_ema = df['EMA_10'].iloc[-1]
    current_stoch_k = df['STOCHk_14_3_3'].iloc[-1]
    
    # NOVOS VALORES DE INDICADORES (RSI e BBANDS)
    current_rsi = df['RSI_14'].iloc[-1]
    bbands_upper = df['BBU_20_2.0'].iloc[-1]
    bbands_lower = df['BBL_20_2.0'].iloc[-1]
    
    conf_call, conf_put, recent_low, recent_high = check_confirmation(df, current_close)
    
    # Status dos Indicadores
    indicator_status = f"ADX: {current_adx:.2f}, EMA(10): {current_ema:.4f}, Stoch K: {current_stoch_k:.2f}, RSI: {current_rsi:.2f}" 
    
    # Preparação da Decisão padrão (Neutro)
    trend, confidence, strategy_used = "NEUTRA", 40, "Análise de Contexto"
    justification = "O mercado está em consolidação e sem sinais claros de extremos. Aguardando novo contexto."

    # --- 1. ESTRATÉGIA DE ALTA PRIORIDADE: BANDAS DE BOLLINGER (Extremos, 90%) ---
    if current_close > bbands_upper:
        strategy_used = "BBANDS Reversão (Sobre-extensão)"
        trend = "PUT"
        confidence = 90
        justification = f"REVERSÃO FORTE. Preço ({current_close:.4f}) acima da Banda Superior de Bollinger ({bbands_upper:.4f})."
        return trend, justification, confidence, indicator_status, strategy_used

    if current_close < bbands_lower:
        strategy_used = "BBANDS Reversão (Sobre-extensão)"
        trend = "CALL"
        confidence = 90
        justification = f"REVERSÃO FORTE. Preço ({current_close:.4f}) abaixo da Banda Inferior de Bollinger ({bbands_lower:.4f})."
        return trend, justification, confidence, indicator_status, strategy_used
        
    # --- 2. ESTRATÉGIA DE ALTA PRIORIDADE: RSI (Reversão Rápida, 88%) ---
    if current_rsi > 70 and conf_put:
        strategy_used = "RSI Reversão (Sobrecompra)"
        trend = "PUT"
        confidence = 88
        justification = f"REVERSÃO RÁPIDA. RSI em SOBRECOMPRA (>70). CONFIRMAÇÃO: {conf_put}."
        return trend, justification, confidence, indicator_status, strategy_used

    if current_rsi < 30 and conf_call:
        strategy_used = "RSI Reversão (Sobrevenda)"
        trend = "CALL"
        confidence = 88
        justification = f"REVERSÃO RÁPIDA. RSI em SOBREVENDA (<30). CONFIRMAÇÃO: {conf_call}."
        return trend, justification, confidence, indicator_status, strategy_used

    # --- 3. DECISÃO DE CONTEXTO (ADX/Stochastic) - Prioridade Padrão ---
    
    if current_adx > 30: # Tendência Forte (Trend-Following, 75%)
        strategy_used = "Acompanhamento de Tendência (EMA Breakout)"
        
        if current_close > current_ema and df['Close'].iloc[-2] > df['EMA_10'].iloc[-2]:
            trend = "CALL"
            confidence = 75
            justification = f"TENDÊNCIA FORTE (ADX {current_adx:.2f}). Preço acima da EMA. CONFIRMAÇÃO: {conf_call if conf_call else 'Nenhuma'}"
            if conf_call: confidence += 10

        elif current_close < current_ema and df['Close'].iloc[-2] < df['EMA_10'].iloc[-2]:
            trend = "PUT"
            confidence = 75
            justification = f"TENDÊNCIA FORTE (ADX {current_adx:.2f}). Preço abaixo da EMA. CONFIRMAÇÃO: {conf_put if conf_put else 'Nenhuma'}"
            if conf_put: confidence += 10

    elif current_adx < 25: # Consolidação (Reversão de Extremos com Stochastic, 85%)
        strategy_used = "Reversão de Extremos (Stochastic Oscillator)"

        if current_stoch_k > 80 and conf_put:
            trend = "PUT"
            confidence = 85
            justification = f"CONSOLIDAÇÃO (ADX {current_adx:.2f}). Stochastic em SOBRECOMPRA (>80). CONFIRMAÇÃO: {conf_put}."

        elif current_stoch_k < 20 and conf_call:
            trend = "CALL"
            confidence = 85
            justification = f"CONSOLIDAÇÃO (ADX {current_adx:.2f}). Stochastic em SOBREVENDA (<20). CONFIRMAÇÃO: {conf_call}."
        
    return trend, justification, confidence, indicator_status, strategy_used

# --- NOVO: FUNÇÃO PARA FILTRO MULTI-TIMEFRAME (30m) ---
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
        add_log("AVISO: Falha ao obter dados MACRO (30m).")
        return "NEUTRA"

    df_macro = pd.DataFrame(response['candles'])
    # Renomear e converter para float
    df_macro = df_macro.rename(columns={'close': 'Close'}).astype(float) 
    
    # Calcular EMA 50 em 30m
    df_macro.ta.ema(length=50, append=True) 
    
    if len(df_macro) < 50 or 'EMA_50' not in df_macro.columns:
        return "NEUTRA"

    current_close_macro = df_macro['Close'].iloc[-1]
    current_ema_macro = df_macro['EMA_50'].iloc[-1]

    if current_close_macro > current_ema_macro:
        return "CALL"
    elif current_close_macro < current_ema_macro:
        return "PUT"
    else:
        return "NEUTRA"
# --- FIM DO FILTRO MTF ---


def fetch_candle_data(ws, symbol, granularity=300):
    """Solicita, analisa (TODOS os indicadores), determina a Tendência e a Estratégia (5m)."""
    granularity_minutes = granularity // 60 
    add_log(f"SOLICITANDO CANDLES de {granularity_minutes}m para análise de tendência...")
    
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

    # 2. VERIFICAÇÃO ROBUSTA (Aceita 'history' ou 'candles' como tipo de mensagem)
    if 'candles' not in response or (response.get('msg_type') != 'history' and response.get('msg_type') != 'candles'):
        add_log(f"AVISO: Resposta de velas inesperada. Tipo de mensagem: {response.get('msg_type')}. Pulando análise.")
        return "NEUTRA", 0, "Resposta de velas incompleta", "ADX: --", "Falha de Dados" 

    
    add_log(f"** DETECTOR DE CANDLES ** Recebidos {len(response['candles'])} velas de {symbol}.")
    
    df = pd.DataFrame(response['candles'])
    df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}).astype(float)
    
    # Cálculo de Indicadores Múltiplos (EXISTENTES)
    df.ta.ema(length=10, append=True)
    df.ta.adx(length=14, append=True)
    df.ta.stoch(k=14, d=3, append=True)
    
    # NOVOS INDICADORES
    df.ta.rsi(length=14, append=True)        
    df.ta.bbands(length=20, append=True)     
    
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
        # Garante que todas as subscrições pendentes sejam removidas
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

                # --- NOVO: FILTRO MACRO (30m) ---
                macro_trend = fetch_macro_trend(ws, symbol)
                add_log(f"** FILTRO MACRO ** Tendência 30m: {macro_trend}")
                # --------------------------------

                # 2. ANÁLISE E SINAL (5m)
                trend, justification, confidence, indicator_status, strategy_used = fetch_candle_data(
                    ws, symbol, granularity=GRANULARITY_SECONDS) 
                
                # --- NOVO: APLICAÇÃO DO FILTRO MTF PARA ASSERTIVIDADE ---
                final_trend = trend
                final_justification = justification
                final_confidence = confidence
                
                # Aumenta a confiança se a tendência 5m for igual à macro (MTF)
                if trend == macro_trend and trend != "NEUTRA":
                    final_confidence = min(100, confidence + 15) # Aumenta 15%
                    final_justification += f" ** CONFIRMAÇÃO MACRO: Tendência 30m é {macro_trend}.**"
                    
                # Zera o sinal se for contra a tendência macro
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
                
                time.sleep(30) # Espera antes de iniciar o próximo ciclo com nova conexão

            except Exception as e:
                add_log(f"ERRO NO CICLO: {e}")
                time.sleep(10) # Espera mais antes de tentar o próximo ciclo se houver erro
            finally:
                if ws:
                    ws.close() # GARANTE O FECHO DA CONEXÃO NO FIM DE CADA CICLO
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
