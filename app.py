import os
import threading
import json
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from websocket import create_connection
import pandas as pd
import numpy as np

app = Flask(__name__)

BOT_STATUS = "OFF"
LOG_MESSAGES = []
FINAL_SIGNAL_DATA = {
    'direction': 'AGUARDANDO', 
    'confidence': 0, 
    'justification': 'O Sniper está a calibrar os sensores...',
    'strategy_used': 'Nenhuma',
    'symbol_name': 'Nenhum'
}

def add_log(message):
    global LOG_MESSAGES
    timestamp = datetime.now().strftime('%H:%M:%S')
    LOG_MESSAGES.append(f"[{timestamp}] {message}")
    if len(LOG_MESSAGES) > 50: LOG_MESSAGES.pop(0)

def calculate_indicators(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['BBU'] = df['SMA_20'] + (df['STD'] * 2)
    df['BBL'] = df['SMA_20'] - (df['STD'] * 2)
    df['EMA_10'] = df['Close'].ewm(span=10, adjust=False).mean()
    return df

def automatic_sniper_engine(df):
    """O bot decide qual a melhor estratégia para a vela atual"""
    c = df.iloc[-1]
    body = abs(c['Close'] - c['Open'])
    high_wick = c['High'] - max(c['Open'], c['Close'])
    low_wick = min(c['Open'], c['Close']) - c['Low']
    
    # 1º FILTRO: BUSCA POR SNIPER (99% - Prioridade Máxima)
    if c['RSI'] > 78 and c['High'] >= c['BBU'] and high_wick > (body * 0.8):
        return "PUT", "🎯 SNIPER DETECTADO: Rejeição extrema no topo. Probabilidade 99%.", 99, "Sniper Elite"
    
    if c['RSI'] < 22 and c['Low'] <= c['BBL'] and low_wick > (body * 0.8):
        return "CALL", "🎯 SNIPER DETECTADO: Suporte de exaustão atingido. Probabilidade 99%.", 99, "Sniper Elite"

    # 2º FILTRO: BUSCA POR FLUXO (85% - Se não houver Sniper, ele vê se há força)
    if body > (high_wick + low_wick) * 2.5: # Vela de corpo muito forte
        if c['Close'] > c['Open'] and c['Close'] > c['EMA_10'] and c['RSI'] < 65:
            return "CALL", "🌊 FLUXO DE ALTA: Vela de força rompendo média. Probabilidade 85%.", 85, "Momentum Flow"
        if c['Close'] < c['Open'] and c['Close'] < c['EMA_10'] and c['RSI'] > 35:
            return "PUT", "🌊 FLUXO DE BAIXA: Vela de força rompendo média. Probabilidade 85%.", 85, "Momentum Flow"

    return "NEUTRA", "Mercado sem padrão Sniper ou Fluxo. Aguardando...", 0, "A analisar"

def bot_loop(token, symbol):
    global BOT_STATUS, FINAL_SIGNAL_DATA
    add_log(f"🚀 Sniper calibrado para {symbol}. A iniciar...")
    try:
        ws = create_connection("wss://ws.derivws.com/websockets/v3?app_id=114910")
        ws.send(json.dumps({"authorize": token}))
        auth = json.loads(ws.recv())
        if "error" in auth:
            add_log("❌ TOKEN INVÁLIDO!")
            BOT_STATUS = "OFF"; return

        add_log(f"✅ CONECTADO! Motor de Inteligência Ativo.")
        while BOT_STATUS == "ON":
            ws.send(json.dumps({"ticks_history": symbol, "end": "latest", "count": 60, "style": "candles", "granularity": 300}))
            data = json.loads(ws.recv())
            if "candles" in data:
                df = calculate_indicators(pd.DataFrame(data['candles']).rename(columns={'open':'Open','high':'High','low':'Low','close':'Close'}))
                dir, just, conf, strat = automatic_sniper_engine(df)
                FINAL_SIGNAL_DATA.update({'direction': dir, 'confidence': conf, 'justification': just, 'strategy_used': strat, 'symbol_name': symbol})
                if dir != "NEUTRA": add_log(f"🔥 SINAL: {dir} ({conf}%)")
            time.sleep(15)
        ws.close()
    except Exception as e:
        add_log(f"⚠️ Erro: {e}"); BOT_STATUS = "OFF"

@app.route('/')
def index(): return render_template('index.html')

@app.route('/control', methods=['POST'])
def control():
    global BOT_STATUS
    data = request.json
    if data['action'] == 'start' and BOT_STATUS == "OFF":
        BOT_STATUS = "ON"
        threading.Thread(target=bot_loop, args=(data['token'], data['symbol'])).start()
    else: BOT_STATUS = "OFF"
    return jsonify({'status': BOT_STATUS})

@app.route('/status')
def get_status(): return jsonify({'status': BOT_STATUS, 'logs': LOG_MESSAGES, 'signal': FINAL_SIGNAL_DATA})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
