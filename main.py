# main.py

import asyncio
import uuid
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, Dict, Any 
import json

# --- IMPORTS CORRETOS ---
# Importa as funções da estratégia
from strategy import generate_signal, get_last_tick_info
from deriv_client import DerivClient
# REMOVIDO: from bots_manager import BotsManager, BotState 

# Variáveis globais
app = FastAPI()
client: Optional[DerivClient] = None
# REMOVIDO: bots_manager: Optional[BotsManager] = None

# Montar pasta static para CSS e JS
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuração de templates
templates = Jinja2Templates(directory=".")

# --- Models Pydantic (para validação de dados) ---
class TokenRequest(BaseModel):
    token: str

# REMOVIDO: class BotCreationRequest(BaseModel):
# REMOVIDO:     ... (Modelos de Bot)

class IAQueryRequest(BaseModel):
    query: str


# --- EVENTOS DE INICIALIZAÇÃO ---
@app.on_event("startup")
async def startup_event():
    """Função executada ao iniciar o servidor."""
    # REMOVIDO: global bots_manager
    # REMOVIDO: bots_manager = BotsManager()
    pass


# --- 1. ROTA PRINCIPAL (INDEX) ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Carrega a página principal do dashboard/login."""
    return templates.TemplateResponse("index.html", {"request": request})

# --- 2. ROTAS DE AUTENTICAÇÃO E CONEXÃO ---

@app.post("/set_token")
async def set_token_and_connect(data: TokenRequest):
    """Recebe o token do usuário, inicia o cliente Deriv e a conexão."""
    global client
    
    # Se já houver um cliente ativo, para o antigo
    if client:
        await client.stop() 

    try:
        # Cria e inicia o novo cliente em segundo plano
        client = DerivClient(data.token)
        # Cria uma tarefa para rodar a conexão sem bloquear o servidor
        asyncio.create_task(client.start()) 
        
        # Espera um pouco para a autorização inicial (pode ser refinado)
        await asyncio.sleep(3) 

        if client.authorized:
            return JSONResponse({
                "ok": True, 
                "message": "Conectado e Autorizado.",
                "account_type": client.account_info['account_type']
            })
        else:
            await client.stop()
            return JSONResponse({"ok": False, "message": "Token inválido ou falha de autorização na Deriv."}, status_code=401)
    except Exception as e:
        print(f"Erro ao iniciar cliente Deriv: {e}")
        return JSONResponse({"ok": False, "message": f"Erro de servidor: {e}"}, status_code=500)


@app.post("/disconnect")
async def disconnect_client():
    """Para o cliente Deriv e limpa a variável global."""
    global client
    if client:
        await client.stop()
        client = None
    # REMOVIDO: O código para parar bots automáticos
    return JSONResponse({"ok": True, "message": "Cliente desconectado."})


@app.get("/status")
async def get_status():
    """Retorna o status atual da conexão e da conta."""
    global client
    
    # REMOVIDO: global bots_manager

    if client and client.connected and client.authorized:
        return {
            "deriv_connected": client.connected,
            "authorized": client.authorized,
            "balance": client.account_info['balance'],
            "account_type": client.account_info['account_type'],
            # Retorna lista vazia de bots, pois o recurso foi removido
            "active_bots": [] 
        }
    
    return {
        "deriv_connected": False,
        "authorized": False,
        "balance": 0.0,
        "account_type": "n/a",
        "active_bots": []
    }


# --- 3. ROTA DE SINAL (ANÁLISE) ---

@app.get("/signal")
async def get_trading_signal(symbol: str = "R_100", tf: str = "60"):
    """
    Gera o sinal de trading e retorna o último tick e a análise.
    symbol e tf são ignorados por enquanto, pois a estratégia é fixa.
    """
    global client

    if not client or not client.connected:
        raise HTTPException(status_code=400, detail="Cliente Deriv não está conectado.")

    # 1. Pega o sinal da estratégia (strategy.py)
    signal_data = generate_signal()

    # 2. Pega o último tick (para exibir na interface)
    last_tick_info = get_last_tick_info()

    return {
        "ok": True,
        "symbol": symbol,
        "tf": tf,
        "last_tick": last_tick_info,
        # Se signal_data for None, o frontend deve interpretar como "AGUARDANDO"
        "signal": signal_data 
    }


# --- 4. ROTAS DE BOTS AUTOMÁTICOS ---

# REMOVIDAS TODAS AS ROTAS DE BOTS:
# @app.post("/bots/create")
# @app.get("/bots/list")
# @app.post("/bots/activate/{bot_id}")
# @app.post("/bots/deactivate/{bot_id}")


# --- 5. ROTA DE IA TRADER ---

@app.post("/ia/query")
async def ia_query(data: IAQueryRequest):
    """Processa a consulta do usuário e retorna uma resposta baseada na IA Trader."""
    
    # Lógica simples de "IA" (Base de Conhecimento Fixo)
    query = data.query.lower()

    if "triângulo ascendente" in query:
        response_text = "O Triângulo Ascendente é um padrão de continuação bullish. É formado por uma linha de resistência horizontal no topo e uma linha de suporte ascendente na base. Sugere que os compradores estão a ganhar força e que uma quebra acima da resistência é provável."
    elif "rsi" in query or "sobrecompra" in query:
        response_text = "O Índice de Força Relativa (RSI) mede a velocidade e a mudança dos movimentos de preço. Um RSI acima de 70 indica sobrecompra (potencial de queda), e um abaixo de 30 indica sobrevenda (potencial de subida)."
    elif "suporte e resistência" in query:
        response_text = "Suporte e Resistência são níveis de preço cruciais onde a pressão de compra ou venda historicamente se concentra. O suporte é um 'piso' onde o preço tende a subir, e a resistência é um 'teto' onde o preço tende a cair."
    elif "bitcoin" in query or "binance" in query:
        response_text = "A análise técnica se aplica a qualquer mercado, incluindo criptomoedas como Bitcoin. No entanto, a alta volatilidade exige cautela e stop-loss mais rígidos."
    else:
        response_text = "Desculpe, a minha base de dados de análise técnica está limitada. Por favor, faça uma pergunta sobre padrões gráficos, indicadores (como RSI/EMA) ou conceitos básicos de trading."

    return JSONResponse({"ok": True, "response": response_text})

