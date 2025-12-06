# main.py

import asyncio
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List
from pydantic import BaseModel
import json

# Importa as dependências
from deriv_client import DerivClient
from bots_manager import manager as bots_manager # Usa a instância única do manager

# Variável principal da aplicação
app = FastAPI()

# --- CONFIGURAÇÃO ---
# O seu index.html usa /static/style.css, então montamos a pasta static
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory=".")


# --- INICIALIZAÇÃO CORRIGIDA ---
# ⚠️ O seu APP_ID é 114910. Vamos inicializar o cliente com este ID.
YOUR_APP_ID = "114910"
deriv_client: DerivClient = DerivClient(app_id=YOUR_APP_ID)


# --- 1. ROTA PRINCIPAL (INDEX) ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Carrega a página principal do dashboard (index.html)."""
    # Note que a página é index.html, conforme enviado
    return templates.TemplateResponse("index.html", {"request": request})

# --- 2. ROTA DE CONEXÃO (CORREÇÃO CRÍTICA DO ERRO 422) ---
@app.post("/set_token")
async def set_token(token: str = Query(..., description="Token de acesso da Deriv")):
    """
    Recebe o token via Query Parameter (corrigido no JS) e inicia a conexão.
    A Rota agora espera o token na URL (?token=...)
    """
    print(f"[API] Recebido Token: {token[:4]}...")
    
    try:
        # Usa o método connect do deriv_client
        await deriv_client.connect(token)
        return JSONResponse({"message": "Token recebido. Conectando à Deriv..."}, status_code=200)
    except Exception as e:
        print(f"[ERRO] Falha ao iniciar conexão: {e}")
        # Retorna erro 400 em caso de token inválido
        raise HTTPException(status_code=400, detail=f"Falha ao conectar: Token inválido ou erro de servidor. {e}")


# --- 3. ROTA DE STATUS ---
@app.get("/status")
async def get_status():
    """Retorna o status atual da conexão e dos bots."""
    
    is_authorized = deriv_client.authorized
    balance = deriv_client.account_info.get("balance", "N/A")
    account_type = deriv_client.account_info.get("account_type", "N/A")

    # Puxa o status dos bots
    active_bots_raw = bots_manager.get_all_bots()
    active_bots_data = [bot.to_dict() for bot in active_bots_raw]
    
    return {
        "is_authorized": is_authorized,
        "balance": balance,
        "account_type": account_type,
        "active_bots": active_bots_data
    }


# --- 4. ROTA DE SINAL (Usada pela Interface e pelos Bots) ---
@app.get("/signal")
async def get_trading_signal(symbol: str = "R_100", tf: int = 5):
    """Calcula e retorna o sinal de trading."""
    
    if not deriv_client.authorized:
        raise HTTPException(status_code=401, detail="Não autorizado. Insira o token primeiro.")

    try:
        # A lógica de cálculo está no deriv_client
        result = deriv_client.calculate_signal(symbol, tf)
        
        if result["action"] == "AGUARDANDO":
            # Retorna 404 se não houver dados suficientes
            raise HTTPException(status_code=404, detail="Aguardando dados suficientes (mínimo 20 ticks).")
            
        return result
        
    except Exception as e:
        print(f"[ERRO SINAL] {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno no cálculo do sinal: {e}")

# --- 5. ROTAS PARA GESTÃO DE BOTS ---

class BotCreationRequest(BaseModel):
    name: str
    symbol: str
    tf: str
    stop_loss: float
    take_profit: float

@app.post("/bots/create")
async def create_bot(req: BotCreationRequest):
    if not deriv_client.authorized:
        raise HTTPException(status_code=401, detail="É necessário estar autorizado para criar bots.")
    
    # Passa o cliente Deriv para o bot manager
    new_bot = bots_manager.create_bot(req.name, req.symbol, req.tf, req.stop_loss, req.take_profit, deriv_client)
    return {"message": "Bot criado com sucesso.", "bot_id": new_bot.id}

@app.post("/bots/activate/{bot_id}")
async def activate_bot(bot_id: str):
    success = bots_manager.activate_bot(bot_id)
    if success:
        return {"message": f"Bot {bot_id[:4]} ativado."}
    raise HTTPException(status_code=404, detail="Bot não encontrado ou já ativo.")

@app.post("/bots/deactivate/{bot_id}")
async def deactivate_bot(bot_id: str):
    success = bots_manager.deactivate_bot(bot_id)
    if success:
        return {"message": f"Bot {bot_id[:4]} desativado."}
    raise HTTPException(status_code=404, detail="Bot não encontrado ou já inativo.")

# Rota para IA (apenas para manter o endpoint do seu frontend)
class IAQueryRequest(BaseModel):
    query: str

@app.post("/ia/query")
async def ia_query(data: IAQueryRequest):
    response_text = "A funcionalidade de IA ainda está em desenvolvimento."
    return JSONResponse({"ok": True, "response": response_text})
    
