import asyncio
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import uvicorn

# Importação das lógicas de estratégia e cliente de conexão
from strategy import generate_signal, get_macro_analysis
from deriv_client import DerivClient

app = FastAPI()

# Variáveis globais de estado do sistema
client: Optional[DerivClient] = None
auto_trading_enabled = False

# Configuração de ficheiros estáticos e templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Modelo de dados para o Login
class TokenRequest(BaseModel):
    token: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Renderiza a interface principal do sistema"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/login")
async def login(data: TokenRequest):
    """
    Realiza a conexão com a Deriv API e autoriza o token.
    Aguardamos 4 segundos para garantir que o handshake do WebSocket foi concluído.
    """
    global client
    try:
        client = DerivClient(token=data.token)
        asyncio.create_task(client.start())
        
        # Tempo necessário para o processo de autorização no deriv_client.py
        await asyncio.sleep(4) 
        
        if client.authorized:
            return {"status": "success"}
        return {"status": "error", "message": "Falha na conexão ou Token Inválido"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/account_info")
async def account_info():
    """Retorna saldo e tipo de conta (Demo/Real)"""
    if client and client.authorized:
        return client.account_info
    return {"balance": 0.0, "account_type": "demo"}

@app.get("/get_analysis")
async def get_analysis():
    """
    Retorna a análise detalhada para o Gráfico Principal e Trade Rápido.
    Utiliza a lógica de confluência do strategy.py.
    """
    sinal = generate_signal()
    if sinal:
        # Retorna o dicionário completo com action, probability, reason e scenario
        return sinal
    return {"status": "waiting", "reason": "Aguardando dados suficientes para análise..."}

@app.get("/macro_stats")
async def macro_stats():
    """Rota para a interface de 'Análise Geral' do menu"""
    return get_macro_analysis()

@app.post("/toggle_auto")
async def toggle_auto(state: bool):
    """Ativa ou desativa a execução automática de ordens"""
    global auto_trading_enabled
    auto_trading_enabled = state
    return {"auto_trading": auto_trading_enabled}

@app.post("/emergency_stop")
async def emergency_stop():
    """
    Interrompe imediatamente todas as operações automáticas.
    Este comando é prioritário e bloqueia novas análises.
    """
    global auto_trading_enabled
    auto_trading_enabled = False
    return {"status": "emergency_triggered", "message": "Sistema interrompido com sucesso"}

# Bloco de execução do servidor
if __name__ == "__main__":
    # Porta 10000 padrão para deploy no Render
    uvicorn.run(app, host="0.0.0.0", port=10000)
