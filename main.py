import asyncio
import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

# Importações dos módulos internos
from strategy import generate_signal, update_ticks
from deriv_client import DerivClient

app = FastAPI(title="Previus-Starps OS Server")

# Configuração de Arquivos Estáticos e Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Globais do Sistema
client: Optional[DerivClient] = None
risk_settings = {
    "stop_loss": 10.0,
    "take_profit": 20.0,
    "min_probability": 0.85
}

# Modelos de Dados para as Requisições
class TokenRequest(BaseModel):
    token: str

class TradeRequest(BaseModel):
    action: str  # 'CALL' ou 'PUT'
    amount: float
    duration: int

class RiskUpdateRequest(BaseModel):
    stop_loss: float
    take_profit: float
    min_prob: float

# --- ROTAS DE NAVEGAÇÃO E INTERFACE ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Carrega a interface principal (SPA)"""
    return templates.TemplateResponse("index.html", {"request": request})

# --- ROTAS DE CONEXÃO E LOGIN ---

@app.post("/login")
async def login(data: TokenRequest):
    """Realiza o login via WebSocket na Deriv"""
    global client
    try:
        # Inicializa o cliente com o APP_ID 114910
        client = DerivClient(token=data.token)
        # Inicia o loop de conexão em segundo plano
        asyncio.create_task(client.start())
        
        # Aguarda validação da Deriv por até 5 segundos
        for _ in range(10):
            await asyncio.sleep(0.5)
            if client.authorized:
                return {"status": "success", "message": "Sistema Conectado"}
        
        return {"status": "error", "message": "Token Inválido ou Exppirado"}
    except Exception as e:
        return {"status": "error", "message": f"Erro de Servidor: {str(e)}"}

# --- ROTAS DE INFORMAÇÃO DA CONTA ---

@app.get("/account_info")
async def account_info():
    """Retorna saldo e tipo de conta em tempo real"""
    if client and client.authorized:
        return {
            "balance": client.account_info["balance"],
            "account_type": client.account_info["account_type"],
            "status": "online"
        }
    return {"balance": 0.0, "account_type": "demo", "status": "offline"}

# --- ROTAS DE ANÁLISE E IA ---

@app.get("/get_analysis")
async def get_analysis():
    """Fornece a análise oportunista para todas as telas"""
    sinal = generate_signal()
    if sinal:
        # Só libera o sinal se atingir a probabilidade mínima de risco
        if sinal["probability"] >= risk_settings["min_probability"]:
            return {"status": "active", **sinal}
    return {"status": "waiting", "reason": "Mercado sem confluência clara"}

# --- ROTAS DE EXECUÇÃO DE TRADE (MANUAL E RÁPIDO) ---

@app.post("/execute_trade")
async def execute_trade(trade: TradeRequest):
    """Executa uma ordem real ou demo na Deriv"""
    if not client or not client.authorized:
        return {"status": "error", "message": "Cliente não autenticado"}
    
    # Aqui entra a lógica de envio do contrato para a Deriv
    # Por segurança, nesta fase, apenas logamos a intenção
    print(f"ORDEM RECEBIDA: {trade.action} | Valor: {trade.amount} | Duração: {trade.duration}")
    
    # Simulação de envio (Próximo passo: Implementar client.buy())
    return {"status": "success", "message": f"Ordem {trade.action} enviada com sucesso!"}

# --- ROTAS DE GESTÃO DE RISCO ---

@app.post("/update_risk")
async def update_risk(settings: RiskUpdateRequest):
    """Atualiza os limites de segurança do bot"""
    global risk_settings
    risk_settings["stop_loss"] = settings.stop_loss
    risk_settings["take_profit"] = settings.take_profit
    risk_settings["min_probability"] = settings.min_prob
    return {"status": "success", "message": "Gestão de Risco Atualizada"}

# --- INICIALIZAÇÃO ---

if __name__ == "__main__":
    # Rodando na porta 10000 (Padrão do Render)
    uvicorn.run(app, host="0.0.0.0", port=10000)
