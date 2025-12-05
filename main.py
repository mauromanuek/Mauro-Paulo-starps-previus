# main.py

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import asyncio
from typing import Optional, Dict, Any

# Importações
from bots_manager import manager as bots_manager, BotState, BotsManager 
from deriv_client import DerivClient
from strategy import generate_signal

# Variável global para o cliente Deriv
deriv_client: Optional[DerivClient] = None

# Inicialização do FastAPI
app = FastAPI()

# ----------------------------------------
# 1. Rotas do Frontend (HTML, CSS)
# ----------------------------------------

# Monta o diretório 'static' (CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve o arquivo index.html principal."""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="index.html não encontrado")

# ----------------------------------------
# 2. Rotas de Conexão e Sinal
# ----------------------------------------

@app.post("/set_token")
async def set_token(token: str):
    """Recebe o token e inicia a conexão com a Deriv."""
    global deriv_client
    
    if deriv_client and deriv_client.connected:
        await deriv_client.stop()

    deriv_client = DerivClient(token=token)
    
    # Inicia a conexão em uma tarefa de background
    asyncio.create_task(deriv_client.start())

    return {"message": "Token recebido e conexão iniciada."}

@app.get("/status")
async def get_status():
    """Retorna o status atual do cliente Deriv e dos bots."""
    global deriv_client

    if deriv_client and deriv_client.authorized:
        # CORREÇÃO PARA O AttributeError: usa o novo método get_all_bots()
        active_bots = bots_manager.get_all_bots() if bots_manager else []
        
        return {
            "is_authorized": deriv_client.authorized,
            "balance": deriv_client.account_info['balance'],
            "account_type": deriv_client.account_info['account_type'],
            "active_bots": [bot.to_dict() for bot in active_bots],
        }
    else:
        return {
            "is_authorized": False,
            "balance": 0.0,
            "account_type": "N/A",
            "active_bots": []
        }

@app.get("/signal", response_model=Optional[Dict[str, Any]])
async def get_signal(symbol: str, tf: int):
    """Gera um sinal de trading com base nos ticks."""
    signal = generate_signal(symbol, tf)
    if signal is None:
        # 404 é retornado se a estratégia não tiver dados suficientes (menos de 20 ticks)
        raise HTTPException(status_code=404, detail="Não há dados suficientes para gerar o sinal (requer 20 ticks).")
    
    return signal

# ----------------------------------------
# 3. Rotas de Gestão de Bots
# ----------------------------------------

@app.post("/bots/create")
async def create_bot(name: str, symbol: str, timeframe: int, sl: float, tp: float):
    """Cria um novo bot e o adiciona à lista."""
    new_bot = bots_manager.create_bot(name, symbol, timeframe, sl, tp)
    return {"message": "Bot criado com sucesso", "bot_id": new_bot.id}

@app.post("/bots/activate/{bot_id}")
async def activate_bot_route(bot_id: str):
    """Ativa o loop de execução de um bot existente."""
    if bots_manager.activate_bot(bot_id):
        return {"message": f"Bot {bot_id} ativado com sucesso."}
    raise HTTPException(status_code=404, detail="Bot não encontrado ou já está ativo.")

@app.post("/bots/deactivate/{bot_id}")
async def deactivate_bot_route(bot_id: str):
    """Desativa o loop de execução de um bot existente."""
    if bots_manager.deactivate_bot(bot_id):
        return {"message": f"Bot {bot_id} desativado com sucesso."}
    raise HTTPException(status_code=404, detail="Bot não encontrado ou já está inativo.")
