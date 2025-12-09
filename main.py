import websocket
import json
import threading
import time
import pandas as pd
import pandas_ta as ta
import os # Necessário para ler a porta do Render (PORT)
from flask import Flask, render_template, request, jsonify
from waitress import serve # Necessário para rodar no Render

# --- CONFIGURAÇÃO DO FLASK E VARIÁVEIS GLOBAIS ---
app = Flask(__name__)

# URL da API WebSocket da Deriv/Binary
WS_URL = "wss://ws.binaryws.com/websockets/v3?app_id=1089" 
MY_APP_ID = 114910
BOT_STATUS = "OFF"
API_TOKEN = None
GRANULARITY_SECONDS = 300  # 5 minutos

# Dados de controlo de estado
current_asset = None
current_mode = None
latest_signal = {
    "status": "AGUARDANDO",
    "direction": "NEUTRA",
    "confidence": 0,
    "justification": "Aguardando autenticação e início do ciclo de análise.",
    "timing": "",
    "logs": []
}

# --- FUNÇÕES DE LÓGICA DE TRADING ---

def log_message(message):
    """Adiciona uma mensagem aos logs de atividade do frontend."""
    timestamp = time.strftime("[%H:%M:%S]")
    full_message = f"{timestamp} {message}"
    
    # Adiciona ao início da lista (logs mais novos primeiro)
    latest_signal['logs'].insert(0, full_message)
    # Limita o número de logs
    if len(latest_signal['logs']) > 50:
        latest_signal['logs'].pop()

def check_stochastic_crossover(df):
    """Verifica condições de sobrevenda/sobrecompra e cruzamento do Stochastic (14, 3, 3)."""
    stoch = df.ta.stoch(k=14, d=3, smooth_k=3, append=True)
    k_line = stoch.iloc[:, 0].dropna()
    d_line = stoch.iloc[:, 1].dropna()

    if k_line.empty or d_line.empty:
        return "NEUTRA", 0, "Stochastic não pôde ser calculado (dados insuficientes)."

    k_now = k_line.iloc[-1]
    d_now = d_line.iloc[-1]
    k_prev = k_line.iloc[-2]
    d_prev = d_line.iloc[-2]

    confidence = 0
    justification = "Nenhuma condição extrema ou cruzamento detectado pelo Stochastic."

    # 1. Sobrecompra (PUT)
    if k_now > 80 and d_now > 80:
        if k_now < d_now and k_prev > d_prev:
            confidence = 85
            justification = f"Stochastic (K={k_now:.2f}, D={d_now:.2f}) em **SOBRECOMPRA** e K cruzou D para baixo. Sinal de **PUT**."
            return "PUT", confidence, justification
    
    # 2. Sobrevenda (CALL)
    if k_now < 20 and d_now < 20:
        if k_now > d_now and k_prev < d_prev:
            confidence = 85
            justification = f"Stochastic (K={k_now:.2f}, D={d_now:.2f}) em **SOBREVENDA** e K cruzou D para cima. Sinal de **CALL**."
            return "CALL", confidence, justification

    # 3. Cruzamento Simples
    if k_now > d_now and k_prev < d_prev:
        return "CALL", 60, f"Stochastic K ({k_now:.2f}) cruzou D ({d_now:.2f}) para cima. Sinal de CALL (Tendência Fraca)."
    elif k_now < d_now and k_prev > d_prev:
        return "PUT", 60, f"Stochastic K ({k_now:.2f}) cruzou D ({d_now:.2f}) para baixo. Sinal de PUT (Tendência Fraca)."
    
    return "NEUTRA", confidence, justification

def check_adx_trend(df):
    """Verifica a força da tendência usando ADX (14) e a direção usando +DI/-DI."""
    adx = df.ta.adx(length=14, append=True)
    
    adx_line = adx.iloc[:, 0].dropna()
    pos_di = adx.iloc[:, 1].dropna()
    neg_di = adx.iloc[:, 2].dropna()

    if adx_line.empty:
        return "NEUTRA", 0, "ADX não pôde ser calculado (dados insuficientes)."
    
    adx_now = adx_line.iloc[-1]
    pos_di_now = pos_di.iloc[-1]
    neg_di_now = neg_di.iloc[-1]

    confidence = 0
    justification = "Nenhuma tendência forte detectada pelo ADX."
    direction = "NEUTRA"

    if adx_now > 30: # Tendência forte
        if pos_di_now > neg_di_now:
            confidence = 90
            direction = "CALL"
            justification = f"ADX está em **{adx_now:.2f} (Forte Tendência de ALTA)**. (+DI > -DI)."
        elif neg_di_now > pos_di_now:
            confidence = 90
            direction = "PUT"
            justification = f"ADX está em **{adx_now:.2f} (Forte Tendência de BAIXA)**. (-DI > +DI)."
    elif adx_now > 20: # Tendência moderada
        if pos_di_now > neg_di_now:
            confidence = 75
            direction = "CALL"
            justification = f"ADX está em **{adx_now:.2f} (Tendência Moderada de ALTA)**."
        elif neg_di_now > pos_di_now:
            confidence = 75
            direction = "PUT"
            justification = f"ADX está em **{adx_now:.2f} (Tendência Moderada de BAIXA)**."
    else:
        justification = f"ADX está em {adx_now:.2f}. Mercado lateral ou fraco. Aguardando tendência."

    return direction, confidence, justification

def check_support_resistance(df, candle_time):
    """Verifica se o preço atual está próximo de um Suporte ou Resistência (S/R) de 50 velas."""
    
    CURRENT_PRICE = df['Close'].iloc[-1]
    S_R_LOOKBACK = 50
    TOLERANCE_PERCENT = 0.001
    TOLERANCE_VALUE = CURRENT_PRICE * TOLERANCE_PERCENT

    MAX_HIGH = df['High'].iloc[-S_R_LOOKBACK:-1].max()
    MIN_LOW = df['Low'].iloc[-S_R_LOOKBACK:-1].min()
        
    confidence = 0
    direction = "NEUTRA"
    justification = "Preço distante de Suporte ou Resistência."

    # 1. Preço próximo de Resistência (Sinal de PUT)
    if (MAX_HIGH - CURRENT_PRICE) <= TOLERANCE_VALUE and CURRENT_PRICE > MAX_HIGH:
        confidence = 90
        direction = "PUT"
        justification = f"Preço rompeu a **RESISTÊNCIA** ({MAX_HIGH:.4f}). Possível sinal de PUT (Pullback/Reversão)."
    elif (MAX_HIGH - CURRENT_PRICE) <= TOLERANCE_VALUE:
        confidence = 80
        direction = "PUT"
        justification = f"Preço próximo da **RESISTÊNCIA** ({MAX_HIGH:.4f}). Possível sinal de PUT (Reversão)."

    # 2. Preço próximo de Suporte (Sinal de CALL)
    if (CURRENT_PRICE - MIN_LOW) <= TOLERANCE_VALUE and CURRENT_PRICE < MIN_LOW:
        confidence = 90
        direction = "CALL"
        justification = f"Preço rompeu o **SUPORTE** ({MIN_LOW:.4f}). Possível sinal de CALL (Pullback/Reversão)."
    elif (CURRENT_PRICE - MIN_LOW) <= TOLERANCE_VALUE:
        confidence = 80
        direction = "CALL"
        justification = f"Preço próximo do **SUPORTE** ({MIN_LOW:.4f}). Possível sinal de CALL (Reversão)."

    return direction, confidence, justification

def check_candlestick_pattern(df):
    """Verifica padrões de Candlestick de Reversão (Martelo, Engolfo)."""
    
    engulfing = df.ta.cdl_engulfing(append=True)
    
    # Engolfo de Alta/Baixa
    if 'CDL_ENGULFING' in engulfing.columns:
        if engulfing['CDL_ENGULFING'].iloc[-2] == 100:
            return "CALL", 90, "Padrão de Candlestick Engolfo de Alta (Bullish) encontrado. Reversão de Baixa para Alta esperada."
        elif engulfing['CDL_ENGULFING'].iloc[-2] == -100:
            return "PUT", 90, "Padrão de Candlestick Engolfo de Baixa (Bearish) encontrado. Reversão de Alta para Baixa esperada."
        
    # Martelo (HAMMER)
    # Usa cdl_pattern que é mais robusto
    hammer = df.ta.cdl_pattern(name="hammer", append=True) 
        
    if 'CDL_HAMMER' in hammer.columns:
        # Martelo de Alta (Hammer - Sinal de CALL)
        if hammer['CDL_HAMMER'].iloc[-2] == 100:
            return "CALL", 85, "Padrão de Candlestick Martelo (Bullish) encontrado. Reversão de Baixa para Alta esperada."
        # Martelo Invertido de Baixa (Inverted Hammer - Sinal de PUT)
        elif hammer['CDL_HAMMER'].iloc[-2] == -100:
            return "PUT", 85, "Padrão de Candlestick Martelo Invertido (Bearish) encontrado. Reversão de Alta para Baixa esperada."

    return "NEUTRA", 0, "Nenhum padrão de candlestick de reversão forte detectado."


def fetch_candle_data(ws, symbol, granularity):
    """Solicita dados de velas à Deriv e executa a análise de tendência."""
    
    request_id = 1
    ws.send(json.dumps({
        "ticks_history": symbol,
        "end": "latest",
        "count": 100,
        "granularity": granularity,
        "style": "candles",
        "subscribe": 0,
        "req_id": request_id
    }))

    response = json.loads(ws.recv())
    
    if 'error' in response:
        log_message(f"ERRO API: Falha ao obter candles: {response['error']['message']}")
        return "NEUTRA", "Falha na requisição de dados.", 0, "ERRO API", "N/A"

    if 'candles' not in response:
        log_message("ERRO: Resposta de candles inválida ou vazia.")
        return "NEUTRA", "Dados de velas vazios.", 0, "ERRO DADOS", "N/A"

    candles = response['candles']
    log_message(f"** DETECTOR DE CANDLES ** Recebidos {len(candles)} velas de {symbol}.")
    
    df = pd.DataFrame(candles)
    df = df.apply(pd.to_numeric)
    df.columns = ['Open', 'High', 'Low', 'Close', 'Date', 'Volume']
    
    # Análise dos Indicadores
    stoch_dir, stoch_conf, stoch_just = check_stochastic_crossover(df)
    adx_dir, adx_conf, adx_just = check_adx_trend(df)
    sr_dir, sr_conf, sr_just = check_support_resistance(df, df['Date'].iloc[-1])
    cdl_dir, cdl_conf, cdl_just = check_candlestick_pattern(df)

    # 4. Estratégia Híbrida de Decisão
    final_dir = "NEUTRA"
    final_conf = 0
    final_just = "Análise concluída. Tendência NEUTRA. Aguardando próximo ciclo."
    strategy_used = "NEUTRA"
    indicator_status = f"ADX: {adx_just} | Stoch: {stoch_just}"
    
    # Estratégia Principal 1: REVERSÃO Forte (Stoch Extremo + S/R + Candlestick)
    if (stoch_conf >= 85 or sr_conf >= 80) and cdl_conf >= 85 and stoch_dir == sr_dir and stoch_dir == cdl_dir:
        final_dir = stoch_dir
        final_conf = 95
        final_just = f"**REVERSÃO FORTE (95%):** {stoch_just} + {sr_just} + {cdl_just}"
        strategy_used = "REVERSÃO HÍBRIDA"
    
    # Estratégia Principal 2: TENDÊNCIA Forte (ADX Forte + Stoch/S/R)
    elif adx_conf >= 90:
        if adx_dir == stoch_dir and stoch_dir != "NEUTRA":
            final_dir = adx_dir
            final_conf = 88
            final_just = f"**TENDÊNCIA FORTE (88%):** ADX Confirma Tendência {adx_dir} + {stoch_just}."
            strategy_used = "ACOMPANHAMENTO ADX"
        elif adx_dir == sr_dir and sr_dir != "NEUTRA":
            final_dir = adx_dir
            final_conf = 85
            final_just = f"**TENDÊNCIA FORTE (85%):** ADX Confirma Tendência {adx_dir} + Preço em Nível de S/R ({sr_just})."
            strategy_used = "ACOMPANHAMENTO ADX"
        else:
            final_just = f"ADX Forte, mas sem confirmação de Momento/Nível. ADX: {adx_just}"
            
    # Estratégia de Confirmação: Reversão de Candlestick em Nível Importante
    elif cdl_conf >= 85 and sr_conf >= 80 and cdl_dir == sr_dir:
        final_dir = cdl_dir
        final_conf = 88
        final_just = f"**REVERSÃO CANDLE (88%):** {cdl_just} em Nível de S/R ({sr_just})."
        strategy_used = "REVERSÃO CANDLE"

    if final_dir == "NEUTRA":
        # Tenta pegar o valor do ADX de forma segura para o log neutro
        try:
            adx_val = df.ta.adx().iloc[:, 0].dropna().iloc[-1]
            final_just = f"Mercado NEUTRO. ADX ({adx_val:.2f}): Aguardando nova tendência ou nível. Stoch: {stoch_just}"
        except IndexError:
             final_just = "Mercado NEUTRO. Dados insuficientes para análise ADX/Stoch."


    return final_dir, final_just, final_conf, indicator_status, strategy_used


def monitor_ticks_and_signal(ws, symbol, trend, confidence, justification, strategy, indicator_status):
    """Monitora o primeiro tick após a análise para garantir o preço de entrada e envia o sinal."""

    request_id = 2
    ws.send(json.dumps({
        "ticks": symbol,
        "subscribe": 1,
        "req_id": request_id
    }))

    log_message("** MONITOR DE TICKS ** Aguardando o primeiro Tick para preço de entrada...")

    try:
        while BOT_STATUS == "ON": # Adicionado verificação para garantir que o bot não para enquanto espera
            response = json.loads(ws.recv())
            
            if 'error' in response:
                log_message(f"ERRO API no Tick: {response['error']['message']}")
                break
            
            if response.get('msg_type') == 'tick':
                tick = response['tick']
                entry_price = tick['bid'] if trend == 'CALL' else tick['ask']
                entry_time = time.strftime('%H:%M:%S', time.gmtime(tick['epoch']))

                ws.send(json.dumps({
                    "forget": tick['id']
                }))
                log_message(f"Tick recebido! Preço de entrada ({trend}): {entry_price:.4f} às {entry_time}.")

                latest_signal.update({
                    "status": "SINAL ATIVO!",
                    "direction": trend,
                    "confidence": confidence,
                    "justification": justification,
                    "timing": f"Entrada (AGORA): {entry_time} | Expiração: +{GRANULARITY_SECONDS}s",
                    "strategy": strategy,
                    "indicators": indicator_status
                })
                break

    except Exception as e:
        log_message(f"Erro no monitor de Ticks: {e}")
        
    finally:
        pass


def websocket_thread(ws_url, api_token, symbol, granularity):
    """Função principal do bot que se conecta e corre o ciclo de análise."""
    global BOT_STATUS

    ws = None
    try:
        log_message("A tentar ligar ao WebSocket...")
        ws = websocket.create_connection(ws_url)
        log_message("Ligação bem-sucedida. A autenticar...")

        # 1. Autenticação
        ws.send(json.dumps({"authorize": api_token}))
        auth_response = json.loads(ws.recv())

        if 'error' in auth_response:
            error_message = auth_response['error'].get('message', 'Erro desconhecido da API.')
            error_code = auth_response['error'].get('code', 'N/A')
            
            # Levanta uma exceção para o erro ser registado nos logs
            raise Exception(f"Autenticação FALHOU. Código da Deriv: {error_code}. Mensagem: {error_message}")
        
        log_message("Autenticação e Conexão estabelecidas com a Deriv.")
        
        # 2. Ciclo de Análise Contínuo
        while BOT_STATUS == "ON":
            
            # 2.1 Fase 1: Análise da Tendência
            log_message(f"SOLICITANDO CANDLES de {int(granularity/60)}m para análise de tendência...")
            trend, justification, confidence, indicator_status, strategy_used = fetch_candle_data(ws, symbol, granularity)
            
            # 2.2 Fase 2: Monitorização do Timing
            if trend != "NEUTRA":
                log_message(f"** SINAL DETETADO ({trend}) ** Confiança: {confidence}%. Justificativa: {justification}")
                monitor_ticks_and_signal(ws, symbol, trend, confidence, justification, strategy_used, indicator_status)
            else:
                latest_signal.update({
                    "status": "AGUARDANDO",
                    "direction": "NEUTRA",
                    "confidence": confidence,
                    "justification": justification,
                    "timing": "",
                    "strategy": strategy_used,
                    "indicators": indicator_status
                })
                log_message(f"Análise concluída. {justification.split('|')[0]}")
            
            # 3. Pausa para o Próximo Ciclo
            wait_time = granularity + 30 
            log_message(f"Aguardando {wait_time} segundos para o próximo ciclo de análise...")
            
            time.sleep(wait_time)


    except websocket.WebSocketTimeoutException:
        log_message("ERRO FATAL: Conexão WebSocket excedeu o tempo limite.")
    except Exception as e:
        log_message(f"ERRO FATAL: {e}")
    finally:
        BOT_STATUS = "OFF"
        latest_signal['status'] = "ERRO - PARADO"
        if ws:
            ws.close()
        log_message("Bot Parado.")


# --- ROTAS FLASK (FRONTEND) ---

@app.route('/')
def index():
    """Rota principal que serve a interface HTML."""
    return render_template('index.html')

@app.route('/control', methods=['POST'])
def control():
    """Rota para iniciar/parar o bot e configurar o Token/Ativo."""
    global BOT_STATUS, API_TOKEN, current_asset, current_mode

    data = request.get_json()
    action = data.get('action')

    if action == 'start':
        if BOT_STATUS == "OFF":
            API_TOKEN = data.get('api_token') # O token é lido do JS a cada vez
            current_asset = data.get('asset')
            current_mode = data.get('mode')
            
            if not API_TOKEN or not current_asset:
                latest_signal['logs'].insert(0, "[ERRO] Token API e Ativo são obrigatórios para iniciar.")
                return jsonify({"status": "error", "message": "Token ou Ativo ausente."})

            BOT_STATUS = "ON"
            latest_signal['status'] = "INICIANDO"
            latest_signal['justification'] = "A ligar ao servidor..."
            
            log_message(f"Iniciando Bot. App ID: {MY_APP_ID}. Ativo: {current_asset}, Modo: {current_mode}.")
            
            thread = threading.Thread(target=websocket_thread, args=(WS_URL, API_TOKEN, current_asset, GRANULARITY_SECONDS))
            thread.start()
            
            return jsonify({"status": "success", "message": "Bot iniciado."})
        else:
            return jsonify({"status": "info", "message": "Bot já está em execução."})
            
    elif action == 'stop':
        if BOT_STATUS == "ON":
            BOT_STATUS = "OFF"
            latest_signal['status'] = "PARANDO"
            latest_signal['justification'] = "A aguardar o fim do ciclo..."
            log_message("Comando de PARAGEM recebido. O bot irá parar após o ciclo atual.")
            return jsonify({"status": "success", "message": "Bot a parar."})
        else:
            return jsonify({"status": "info", "message": "Bot já está parado."})
    
    return jsonify({"status": "error", "message": "Ação desconhecida."})

@app.route('/status')
def get_status():
    """Rota para o frontend obter o status atual do bot e os logs."""
    latest_signal['current_status'] = BOT_STATUS
    latest_signal['asset'] = current_asset
    latest_signal['mode'] = current_mode
    return jsonify(latest_signal)

if __name__ == '__main__':
    log_message("Servidor Flask inicializado. Acesse a interface para iniciar o bot.")
    
    try:
        # Usa a porta fornecida pelo Render
        port = int(os.environ.get('PORT', 5000))
        serve(app, host='0.0.0.0', port=port)
    except Exception as e:
        log_message(f"Falha ao iniciar o servidor: {e}. Usando fallback.")
        app.run(host='0.0.0.0', port=5000)
