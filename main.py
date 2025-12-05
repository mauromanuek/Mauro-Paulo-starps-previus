# main.py

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
from typing import Optional, List, Dict, Any

# Importar os módulos do seu projeto
from deriv_client import DerivClient
from bots_manager import manager as bots_manager 

# 1. Variável 'app' deve ser global para o Uvicorn
app = FastAPI()

# --- Configuração ---
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory=".")

# 2. CORREÇÃO CRÍTICA: Inicializa o cliente Deriv COM O APP_ID
# Você precisa de encontrar o seu APP_ID (geralmente um número pequeno, ex: 1089)
YOUR_APP_ID = "YOUR_APP_ID_HERE"  # <<<< INSIRA O SEU APP_ID AQUI >>>>
deriv_client = DerivClient(app_id=YOUR_APP_ID)


# --- Rotas da API (Backend) ---

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    """Serve o arquivo index.html principal."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/set_token")
async def set_token(token: str = Query(..., description="Token de acesso da Deriv")):
    """Recebe e processa o token de acesso."""
    print(f"Recebido Token: {token[:4]}...")
    
    try:
        await deriv_client.connect(token)
        return {"message": "Token recebido. Conectando à Deriv..."}
    except Exception as e:
        print(f"Erro ao iniciar conexão: {e}")
        raise HTTPException(status_code=500, detail=f"Falha ao conectar: {e}")

@app.get("/status")
async def get_status():
    """Retorna o status atual da conexão para a interface."""
    
    is_authorized = deriv_client.is_authorized
    balance = deriv_client.account_info.get("balance", "N/A") if deriv_client.account_info else "N/A"
    account_type = deriv_client.account_info.get("account_type", "N/A") if deriv_client.account_info else "N/A"

    active_bots_raw = bots_manager.get_all_bots() if bots_manager else []
    active_bots_data = [bot.to_dict() for bot in active_bots_raw]
    
    return {
        "is_authorized": is_authorized,
        "balance": balance,
        "account_type": account_type,
        "active_bots": active_bots_data
    }

@app.get("/signal")
async def get_trading_signal(symbol: str = "R_100", tf: int = 5):
    """Calcula e retorna o sinal de trading."""
    
    if not deriv_client.is_authorized:
        raise HTTPException(status_code=401, detail="Não autorizado. Insira o token primeiro.")

    try:
        result = deriv_client.calculate_signal(symbol, tf)
        
        if result["action"] == "AGUARDANDO":
            raise HTTPException(status_code=404, detail="Aguardando dados suficientes (mínimo 20 ticks).")
            
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno no cálculo do sinal: {e}")


# --- Rotas para Gestão de Bots ---

@app.post("/bots/create")
async def create_bot(name: str, symbol: str, timeframe: int, sl: float, tp: float):
    if not deriv_client.is_authorized:
        raise HTTPException(status_code=401, detail="É necessário estar autorizado para criar bots.")
    
    new_bot = bots_manager.create_bot(name, symbol, timeframe, sl, tp)
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
    
