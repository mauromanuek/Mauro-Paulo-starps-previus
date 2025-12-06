# main.py

import asyncio
import uuid
from fastapi import FastAPI, Request, HTTPException, JSONResponse, Query # <-- ADICIONADO 'Query' E 'JSONResponse'
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json

# --- IMPORTS CORRETOS ---
from strategy import generate_signal 
from deriv_client import DerivClient
from bots_manager import BotsManager, BotState 

# Variáveis globais
app = FastAPI()
client: Optional[DerivClient] = None
bots_manager: Optional[BotsManager] = None

# Montar pasta static para CSS e JS
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuração de templates
templates = Jinja2Templates(directory=".")

# --- Models Pydantic (para validação de dados) ---
# A classe TokenRequest já não é necessária, mas mantemos as outras.
class BotCreationRequest(BaseModel):
    name: str
    symbol: str
    tf: str
    stop_loss: float
    take_profit: float

class IAQueryRequest(BaseModel):
    query: str


# --- EVENTOS DE INICIALIZAÇÃO ---
@app.on_event("startup")
async def startup_event():
    """Função executada ao iniciar o servidor."""
    global bots_manager
    bots_manager = BotsManager()

# --- 1. ROTA PRINCIPAL (INDEX) ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Carrega a página principal do aplicativo."""
    return templates.TemplateResponse("index.html", {"request": request}) 


# --- 2. ROTA CRÍTICA: SET TOKEN (CORRIGIDA) ---
@app.post("/set_token")
async def set_token_and_start_client(token: str = Query(..., description="O Token API da Deriv")):
    """
    Recebe o token API como um parâmetro de query (Query Parameter) e inicia o cliente Deriv.
    CORREÇÃO CRÍTICA PARA ELIMINAR ERRO 422 NO RENDER.
    """
    global client
    
    if client and client.connected:
        raise HTTPException(status_code=400, detail="O cliente já está conectado. Desconecte primeiro.")

    # 1. Cria e inicia o cliente Deriv
    client = DerivClient(token=token)
    
    # Executa a função start em segundo plano para não bloquear a resposta HTTP
    asyncio.create_task(client.start())
    
    # Retorna uma resposta imediata de sucesso
    return JSONResponse({"ok": True, "message": "Cliente Deriv a iniciar a conexão."})


# --- 3. ROTA DE STATUS ---
@app.get("/status")
async def get_status():
    """Retorna o status da conexão, saldo e bots ativos."""
    is_authorized = client.authorized if client else False
    balance = client.account_info.get("balance", 0.0) if client else 0.0
    account_type = client.account_info.get("account_type", "demo") if client else "demo"
    
    # Busca a lista de bots para enviar ao frontend
    active_bots_data = []
    if bots_manager:
        for bot in bots_manager.get_all_bots():
            active_bots_data.append({
                "id": bot.id,
                "name": bot.name,
                "symbol": bot.symbol,
                "tf": bot.tf,
                "stop_loss": bot.stop_loss,
                "take_profit": bot.take_profit,
                "is_active": bot.is_active
            })

    return JSONResponse({
        "is_authorized": is_authorized,
        "balance": balance,
        "account_type": account_type,
        "active_bots": active_bots_data
    })


# --- 4. ROTA DE SINAL (ANÁLISE MANUAL) ---
@app.get("/signal")
async def get_trading_signal(symbol: str, tf: str):
    """Gera um sinal de trading com base nos dados mais recentes."""
    
    if not client or not client.authorized:
        raise HTTPException(status_code=401, detail="Não Autorizado. Conecte o Token API primeiro.")

    # Usa a função de estratégia
    signal_data = generate_signal()

    if not signal_data:
        # Retorna 404 se não houver dados suficientes para análise (ex: menos de 20 ticks)
        raise HTTPException(status_code=404, detail="Dados insuficientes para gerar um sinal (mínimo 20 ticks). Aguardando mais dados.")
    
    # Adiciona metadados ao sinal
    signal_data["symbol"] = symbol
    signal_data["tf"] = tf
    
    return JSONResponse(signal_data)


# --- 5. ROTAS DE GESTÃO DE BOTS ---

@app.post("/bots/create")
async def create_new_bot(data: BotCreationRequest):
