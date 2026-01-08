import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

# Imports dos componentes que você já possui
from deriv_client import DerivClient
from bots_manager import BotsManager
from strategy import generate_signal

app = FastAPI(title="Previus-Starps OS")

# Configurações globais
client: Optional[DerivClient] = None
bots_manager = BotsManager()

# Montagem de arquivos estáticos (CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Modelo de dados para o Login
class TokenRequest(BaseModel):
    token: str

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Carrega a interface principal"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/login")
async def login(data: TokenRequest):
    """Realiza a conexão com a Deriv usando o Token fornecido"""
    global client
    try:
        # Inicializa o cliente com o Token digitado pelo usuário
        client = DerivClient(token=data.token)
        # Tenta iniciar a conexão WebSocket
        asyncio.create_task(client.start())
        
        return {"status": "success", "message": "Conectando à Deriv..."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/get_analysis")
async def get_analysis():
    """Rota que a interface chama para ver a previsão da IA"""
    if not client or not client.authorized:
        return {"status": "offline", "analysis": "Aguardando conexão..."}
    
    # Chama sua lógica de estratégia (Price Action + RSI)
    sinal = generate_signal()
    
    if sinal:
        return {
            "status": "active",
            "action": sinal['action'],
            "prob": f"{sinal['probability'] * 100}%",
            "reason": sinal['reason']
        }
    else:
        return {"status": "waiting", "analysis": "Analisando fluxo de ticks..."}

@app.get("/account_info")
async def account_info():
    """Retorna saldo e tipo de conta"""
    if client and client.authorized:
        return client.account_info
    return {"balance": 0.0, "account_type": "None"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
