# main.py - Versão FINAL E COMPLETA: CORS, Conexão Assíncrona e Lógica de Erros

import asyncio
import uuid
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json

from fastapi.middleware.cors import CORSMiddleware 

from strategy import generate_signal # Importa a função de sinal adaptativa
from deriv_client import DerivClient
from bots_manager import BotsManager, BotState 

# Variáveis globais
app = FastAPI()
client: Optional[DerivClient] = None
bots_manager: Optional[BotsManager] = None

# --- ADIÇÃO DO MIDDLEWARE CORS ---
origins = [
    "*" 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)
# ---------------------------------


# Montar pasta static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuração de templates
templates = Jinja2Templates(directory=".")

# --- Models Pydantic ---
class TokenRequest(BaseModel):
    token: str

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
    global bots_manager
    bots_manager = BotsManager()

# --- 1. ROTA PRINCIPAL (INDEX) ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# --- 2. ROTA DE AUTORIZAÇÃO (POST) ---
@app.post("/set_token", response_class=JSONResponse)
async def set_token(data: TokenRequest):
    """Lida com a conexão e autorização do token da Deriv."""
    global client, bots_manager
    
    if client:
        await client.stop() 
        client = None

    client = DerivClient(data.token, bots_manager) 
    
    try:
        # 1. Inicia a conexão em TAREFA DE FUNDO
        asyncio.create_task(client.connect_and_subscribe(symbol="R_100")) 

        # 2. Esperar pela autorização E carregamento de histórico (AUMENTADO PARA 10s)
        for _ in range(20): # Espera no máximo 10 segundos (20 * 0.5s)
            
            # --- CONDIÇÃO DE SUCESSO MELHORADA: Autorizado E Histórico Carregado ---
            if client.authorized and client.history_loaded:
                return JSONResponse({
                    "ok": True, 
                    "message": "Conectado, Autorizado e Histórico de Velas Carregado. O bot está PRONTO.",
                    "account_type": client.account_info.get("account_type"),
                    "balance": client.account_info.get("balance")
                })
            
            # Se a conexão falhou (erro de rede/token) e não está autorizado
            if not client.is_connected and not client.authorized and client.ws is None:
                 await client.stop()
                 raise HTTPException(status_code=401, detail="Conexão Falhou: Token inválido, expirado ou problema de rede (veja o log do servidor).")
            
            await asyncio.sleep(0.5)

        # Se o loop terminar sem a condição de sucesso (TIMEOUT)
        await client.stop()
        raise HTTPException(status_code=401, detail="Token inválido, falha na autorização ou o histórico de velas não carregou a tempo (Timeout).")
        
    except HTTPException as e:
        # Re-lança o HTTPException para ser capturado pelo FastAPI
        raise e
    except Exception as e:
        # Captura erros inesperados
        if client:
            await client.stop()
            client = None
        raise HTTPException(status_code=500, detail=f"Erro fatal ao conectar: {str(e)}")


# --- 3. ROTA DE STATUS (GET) ---
@app.get("/status", response_class=JSONResponse)
async def get_status():
    global client
    status = {
        "connected": client and client.connected, 
        "authorized": client and client.authorized, 
        # Informa se os dados estão prontos
        "data_ready": client and client.authorized and client.history_loaded,
        "balance": client.account_info.get("balance", 0.0) if client else 0.0,
        "account_type": client.account_info.get("account_type", "offline") if client else "offline"
    }
    return JSONResponse(status)


# --- 4. ROTA DE SINAL (GET) ---
@app.get("/signal")
async def get_signal(symbol: str = "R_100"):
    # Verifica se os dados estão prontos antes de analisar
    if not client or not (client.authorized and client.history_loaded):
        raise HTTPException(status_code=404, detail="Não autorizado ou Histórico de Velas ainda não carregado. Aguarde e tente novamente.")
    
    signal = generate_signal(symbol, "1m") 
        
    if signal is not None:
        return signal
    
    # Este erro só deve ocorrer se MIN_TICKS_REQUIRED > len(ticks_history), o que não deve acontecer após o carregamento
    raise HTTPException(
        status_code=404, 
        detail=f"Não há dados suficientes para calcular todos os indicadores ({MIN_TICKS_REQUIRED} mínimos)."
    )

# ... (restante do main.py, rotas de bots e IA, permanece inalterado) ...
# Para brevidade, as rotas /bot/create, /bots/list, /bot/pause e /ia/query não estão aqui, mas devem ser mantidas no seu ficheiro.

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
