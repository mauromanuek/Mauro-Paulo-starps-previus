# main.py

import asyncio
import uuid
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json

# --- IMPORTS CORRETOS ---
# Importa as funções da estratégia, não a classe antiga
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
    """Função executada ao iniciar o servidor."""
    global bots_manager
    bots_manager = BotsManager()

# --- 1. ROTA PRINCIPAL (INDEX) ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Carrega a página principal do dashboard/login."""
    return templates.TemplateResponse("index.html", {"request": request})

# --- 2. ROTAS DE AUTENTICAÇÃO E CONEXÃO ---

@app.post("/set_token")
async def set_token_and_connect(data: TokenRequest):
    """Recebe o token do usuário e inicia a conexão com a Deriv."""
    global client
    
    # Se o cliente já estiver rodando, pare-o
    if client and client.connected:
        await client.stop()

    client = DerivClient(token=data.token)
    
    # Inicia a conexão em segundo plano
    asyncio.create_task(client.start())
    
    # Não espera a conexão terminar, retorna imediatamente
    return JSONResponse({"ok": True, "message": "Conexão iniciada. Verifique o status em breve."})

@app.get("/status")
async def get_status():
    """Retorna o status atual da conexão e da conta."""
    global client
    global bots_manager

    if client and client.connected and client.authorized:
        return {
            "deriv_connected": client.connected,
            "authorized": client.authorized,
            "balance": client.account_info['balance'],
            "account_type": client.account_info['account_type'],
            "active_bots": [bot.to_dict() for bot in bots_manager.get_all_bots()] if bots_manager else []
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
async def get_signal(symbol: str, tf: str):
    """
    Gera e retorna um sinal de trading com base na análise dos ticks.
    """
    if not client or not client.authorized:
        raise HTTPException(status_code=401, detail="Não autorizado. Faça o login primeiro.")
    
    # A lógica da estratégia está no strategy.py
    signal = generate_signal(symbol, tf)
    
    if signal is None:
        # Retorna 404 se não houver dados suficientes ou o sinal não estiver pronto
        raise HTTPException(status_code=404, detail="Não há dados suficientes para gerar o sinal (requer 20 ticks).")
    
    return signal

# --- 4. ROTAS DE BOTS AUTOMÁTICOS ---

@app.post("/bots/create")
async def create_new_bot(data: BotCreationRequest):
    """Cria e inicia um novo bot."""
    global bots_manager

    if not client or not client.authorized or not bots_manager:
        raise HTTPException(status_code=401, detail="Não autorizado ou Manager não inicializado.")

    bot = bots_manager.create_bot(
        name=data.name,
        symbol=data.symbol,
        tf=data.tf,
        stop_loss=data.stop_loss,
        take_profit=data.take_profit,
        client=client 
    )
    
    # Inicia a tarefa do bot em segundo plano
    asyncio.create_task(bot.run_bot_loop())
    
    return JSONResponse({"ok": True, "id": bot.id, "message": f"Bot '{data.name}' criado e iniciado."})

@app.post("/bots/activate/{bot_id}")
async def activate_bot(bot_id: str):
    """Ativa um bot existente."""
    global bots_manager
    if not bots_manager:
        raise HTTPException(status_code=500, detail="Bots Manager não inicializado.")
    
    bot = bots_manager.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot não encontrado.")

    if bot.is_active:
        return JSONResponse({"ok": True, "message": "Bot já está ativo."})
    
    bot.state = BotState.ACTIVE
    asyncio.create_task(bot.run_bot_loop())
    return JSONResponse({"ok": True, "message": f"Bot ID {bot_id} ativado."})

@app.post("/bots/deactivate/{bot_id}")
async def deactivate_bot(bot_id: str):
    """Desativa um bot existente."""
    global bots_manager
    if not bots_manager:
        raise HTTPException(status_code=500, detail="Bots Manager não inicializado.")

    bot = bots_manager.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot não encontrado.")

    if not bot.is_active:
        return JSONResponse({"ok": True, "message": "Bot já está inativo."})
    
    bot.state = BotState.INACTIVE
    return JSONResponse({"ok": True, "message": f"Bot ID {bot_id} desativado."})


# --- 5. ROTA DE IA TRADER ---

@app.post("/ia/query")
async def ia_query(data: IAQueryRequest):
    """Simula uma resposta de IA para perguntas de trading."""
    # Simulação: Em um projeto real, aqui você usaria um modelo de LLM (como Gemini, GPT)
    
    # Lógica de resposta simples (simulação de IA)
    response_text = ""
    query = data.query.lower()

    if "triângulo ascendente" in query:
        response_text = "O Triângulo Ascendente é um padrão de continuação bullish. É formado por uma linha de resistência horizontal no topo e uma linha de suporte ascendente na base. Sugere que os compradores estão a ganhar força e que uma quebra acima da resistência é provável. [attachment_0](attachment)"
    elif "rsi" in query or "sobrecompra" in query:
        response_text = "O Índice de Força Relativa (RSI) mede a velocidade e a mudança dos movimentos de preço. Um RSI acima de 70 indica sobrecompra (potencial de queda), e um abaixo de 30 indica sobrevenda (potencial de subida)."
    elif "suporte e resistência" in query:
        response_text = "Suporte e Resistência são níveis de preço cruciais onde a pressão de compra ou venda historicamente se concentra. O suporte é um 'piso' onde o preço tende a subir, e a resistência é um 'teto' onde o preço tende a cair. [attachment_1](attachment)"
    elif "bitcoin" in query or "binance" in query:
        response_text = "A análise técnica se aplica a qualquer mercado, incluindo criptomoedas como Bitcoin. No entanto, a alta volatilidade exige cautela e stop-loss mais rígidos."
    else:
        response_text = "Desculpe, a minha base de dados de análise técnica está limitada. Por favor, faça uma pergunta sobre padrões gráficos, indicadores (como RSI/EMA) ou conceitos básicos de trading."

    return JSONResponse({"ok": True, "response": response_text})

