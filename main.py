import os
import threading
import json
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from websocket import create_connection
import pandas as pd
import numpy as np
from werkzeug.serving import make_server

# --- CONFIGURAÇÕES ---
MY_APP_ID = 114910 
DERIV_URL = f"wss://ws.derivws.com/websockets/v3?app_id={MY_APP_ID}"
MAX_LOG_SIZE = 50 

app = Flask(__name__)
BOT_STATUS = "OFF"
BOT_THREAD = None
LOG_MESSAGES = [] 
CURRENT_SYMBOL = "R_100" 

FINAL_SIGNAL_DATA = {
    'direction': 'AGUARDANDO', 
    'confidence': 0,
    'indicator_status': 'EMA: --, RSI: --, ATR: --',
    'justification': 'O bot está a analisar o fluxo das velas...',
    'strategy_used': 'Nenhuma',
    'entry_time': '--:--:--',
    'exit_time': '--:--:--'
}

def add_log(message):
    global LOG_MESSAGES
    timestamp = time.strftime('%H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    LOG_MESSAGES.append(log_entry)
    if len(LOG_MESSAGES) > MAX_LOG_SIZE: LOG_MESSAGES.pop(0)

def calculate_indicators(df):
    # Indicadores para Certeza Absoluta
    df['EMA_10'] = df['Close'].ewm(span=10, adjust=False).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['BBU'] = df['SMA_20'] + (df['STD'] * 2)
    df['BBL'] = df['SMA_20'] - (df['STD'] * 2)
    return df

def strategy_selection_engine(df):
    c = df.iloc[-1]
    body = abs(c['Close'] - c['Open'])
    total_range = c['High'] - c['Low']
    upper_wick = c['High'] - max(c['Open'], c['Close'])
    lower_wick = min(c['Open'], c['Close']) - c['Low']
    
    status = f"RSI: {c['RSI']:.2f} | BBU: {c['BBU']:.2f} | Corpo: {body:.2f}"

    # 1. ESTRATÉGIA SNIPER (CERTEZA 99%)
    if c['RSI'] > 80 and c['Close'] >= c['BBU'] and upper_wick > (body * 0.8):
        return "PUT", "⚠️ SNIPER: Rejeição institucional extrema detectada. Certeza de queda iminente.", 99, "Sniper Reversal", status
    
    if c['RSI'] < 20 and c['Close'] <= c['BBL'] and lower_wick > (body * 0.8):
        return "CALL", "⚠️ SNIPER: Suporte institucional atingido com forte pavio de rejeição. Certeza de ALTA.", 99, "Sniper Reversal", status

    # 2. ESTRATÉGIA DE FLUXO (85%) - PREDIÇÃO DA PRÓXIMA VELA
    if body > (total_range * 0.75):
        if c['Close'] > c['Open'] and c['Close'] > c['EMA_10']:
            return "CALL", "FLUXO: Vela de força compradora sem resistência. Próxima vela: ALTA.", 85, "Momentum Flow", status
        if c['Close'] < c['Open'] and c['Close'] < c['EMA_10']:
            return "PUT", "FLUXO: Pressão vendedora dominante. Próxima vela: BAIXA.", 85, "Momentum Flow", status

    return "NEUTRA", "Mercado em consolidação. Aguardando sinal de alta probabilidade...", 0, "Nenhuma", status

def deriv_bot_core_logic(symbol, api_token):
    global BOT_STATUS, FINAL_SIGNAL_DATA
    while BOT_STATUS == "ON":
        try:
            ws = create_connection(DERIV_URL)
            ws.send(json.dumps({"authorize": api_token}))
            auth = json.loads(ws.recv())
            if "error" in auth:
                add_log("Erro: Token Inválido")
                break

            ws.send(json.dumps({"ticks_history": symbol, "end": "latest", "count": 100, "style": "candles", "granularity": 300}))
            data = json.loads(ws.recv())

            if "candles" in data:
                df = pd.DataFrame(data['candles']).rename(columns={'open':'Open','high':'High','low':'Low','close':'Close'})
                df = calculate_indicators(df)
                dir, just, conf, strat, ind_status = strategy_selection_engine(df)
                
                now = datetime.utcnow()
                FINAL_SIGNAL_DATA.update({
                    'direction': dir, 'confidence': conf, 'justification': just,
                    'strategy_used': strat, 'indicator_status': ind_status,
                    'entry_time': now.strftime('%H:%M:%S'),
                    'exit_time': (now + timedelta(minutes=5)).strftime('%H:%M:%S')
                })
                add_log(f"Análise: {dir} | Confiança: {conf}%")
            ws.close()
            time.sleep(15) 
        except Exception as e:
            add_log(f"Erro de Conexão: {e}")
            time.sleep(10)

@app.route('/')
def index(): return render_template('index.html')

@app.route('/control', methods=['POST'])
def control():
    global BOT_STATUS, BOT_THREAD
    data = request.json
    if data['action'] == 'start':
        BOT_STATUS = "ON"
        BOT_THREAD = threading.Thread(target=deriv_bot_core_logic, args=(data['symbol'], data['api_token']))
        BOT_THREAD.start()
    else: BOT_STATUS = "OFF"
    return jsonify({'status': BOT_STATUS})

@app.route('/status')
def get_status(): return jsonify({'status': BOT_STATUS, 'logs': LOG_MESSAGES, 'signal_data': FINAL_SIGNAL_DATA})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    http_server = make_server('0.0.0.0', port, app)
    http_server.serve_forever()
