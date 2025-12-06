# main.py

import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Any
import json
import os
import uuid

# --- IMPORTS CORRETOS ---
# Mantém a sua estrutura original de imports
from strategy import calculate_indicators, generate_signal, update_ticks 
from deriv_client import DerivClient
from bots_manager import BotsManager, BotState 

# Variáveis globais
app = FastAPI()
client: Optional[DerivClient] = None
bots_manager: Optional[BotsManager] = None

# Montar pasta static para CSS e JS (garantir que o style.css é lido)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Tenta carregar o HTML principal
try:
    with open("index.html", "r", encoding="utf-8") as f:
        INDEX_HTML = f.read()
except FileNotFoundError:
    INDEX_HTML = "<h1>Erro: index.html não encontrado.</h1>"

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
    """Carrega a página principal do aplicativo."""
    return HTMLResponse(INDEX_HTML)

# --- 2. ROTAS DE STATUS E LOGIN ---
@app.get("/status")
async def status_route():
    """Retorna o status da conexão, autorização e saldo."""
    global client
    if not client:
        return {"connected": False, "authorized": False, "balance": 0.0, "currency": "USD", "account_type": "n/a"}
    
    return {
        "connected": client.connected,
        "authorized": client.authorized,
        "balance": client.account_info.get("balance", 0.0),
        "currency": client.account_info.get("currency", "USD"),
        "account_type": client.account_info.get("account_type", "n/a"),
    }

@app.post("/set_token")
async def set_token_route(data: TokenRequest): 
    """Recebe o token do front-end e inicia/reinicia a conexão."""
    global client
    if not data.token:
        raise HTTPException(status_code=400, detail="Token não fornecido.")
    
    # Se o cliente já existir e estiver rodando, paramos.
    if client:
        await client.stop() 
        
    client = DerivClient(data.token) # Cria nova instância com o novo token
    asyncio.create_task(client.start()) # Inicia o loop em background

    # 🟢 CRÍTICO: Registra o cliente no manager para que ele possa criar bots
    global bots_manager
    if bots_manager:
        bots_manager.set_client(client) 

    return JSONResponse({"success": True, "message": "Conexão em segundo plano iniciada."})

# --- 3. ROTAS DE ANÁLISE MANUAL ---

@app.get("/signal/{symbol}")
async def get_signal(symbol: str):
    """Retorna o sinal de trading em tempo real para o símbolo."""
    
    # 🟢 A lógica do seu strategy.py usa o estado global (ticks_history)
    indicators = calculate_indicators()
    
    if not indicators:
         raise HTTPException(status_code=404, detail="Dados de ticks insuficientes (Mínimo de 20 ticks).")
    
    # O generate_signal do seu arquivo recebe os indicadores
    signal_data = generate_signal(indicators) 
    
    # O seu strategy.py retorna um dicionário se houver sinal, senão None
    if signal_data is None:
        signal_data = {
             "action": "AGUARDANDO",
             "probability": 0.0,
             "reason": "Condições de mercado neutras ou insuficientes.",
             "explanation": "Nenhum sinal forte encontrado.",
        }

    # Adiciona o preço atual ao retorno para o frontend
    signal_data["current_price"] = indicators.get("last_price", 0.0)

    return JSONResponse(signal_data)

# --- 4. ROTAS DE BOTS ---

@app.post("/create_bot")
async def create_bot_route(data: BotCreationRequest):
    """Cria e regista um novo bot."""
    global client, bots_manager
    if not client or not client.authorized:
        raise HTTPException(status_code=401, detail="Não autorizado. Faça login primeiro.")
        
    bot = bots_manager.create_bot(
        name=data.name,
        symbol=data.symbol,
        tf=data.tf,
        stop_loss=data.stop_loss,
        take_profit=data.take_profit,
        client=client
    ) 
    # Ativa-o imediatamente
    bots_manager.toggle_bot_state(bot.id, BotState.ACTIVE) 
    
    # 🟢 CRÍTICO: Subscreve o novo símbolo no DerivClient
    await client.subscribe_to_ticks(data.symbol) 

    return JSONResponse({"success": True, "id": bot.id, "message": "Bot criado e ativado."})

@app.get("/bots")
async def list_bots_route():
    """Lista todos os bots ativos/inativos."""
    global bots_manager
    return bots_manager.get_all_bots_info()

@app.post("/bot/{bot_id}/activate")
async def activate_bot_route(bot_id: str):
    """Ativa um bot existente."""
    global bots_manager
    if not bots_manager.toggle_bot_state(bot_id, BotState.ACTIVE):
        raise HTTPException(status_code=404, detail="Bot não encontrado.")
    return JSONResponse({"success": True, "message": f"Bot {bot_id} ativado."})

@app.post("/bot/{bot_id}/deactivate")
async def deactivate_bot_route(bot_id: str):
    """Desativa um bot existente."""
    global bots_manager
    if not bots_manager.toggle_bot_state(bot_id, BotState.INACTIVE):
        raise HTTPException(status_code=404, detail="Bot não encontrado ou erro ao parar.")
    return JSONResponse({"success": True, "message": f"Bot {bot_id} desativado."})

# --- 5. ROTA DE IA TRADER (Mantida) ---
@app.post("/ia/query")
async def ia_query(data: IAQueryRequest):
    """Simula uma resposta de IA para perguntas de trading."""
    # Sua lógica existente de IA
    response_text = ""
    query = data.query.lower()

    if "triângulo ascendente" in query:
        response_text = "O Triângulo Ascendente é um padrão de continuação bullish. É formado por uma linha de resistência horizontal no topo e uma linha de suporte ascendente na base. Sugere que os compradores estão a ganhar força e que uma quebra acima da resistência é provável."
    elif "rsi" in query or "sobrecompra" in query:
        response_text = "O Índice de Força Relativa (RSI) mede a velocidade e a mudança dos movimentos de preço. Um RSI acima de 70 indica sobrecompra (potencial de queda), e um abaixo de 30 indica sobrevenda (potencial de subida)."
    elif "suporte e resistência" in query:
        response_text = "Suporte e Resistência são níveis de preço cruciais onde a pressão de compra ou venda historicamente se concentra. O suporte é um 'piso' onde o preço tende a subir, e a resistência é um 'teto' onde o preço tende a cair."
    else:
        response_text = "Desculpe, a minha base de dados de análise técnica está limitada. Por favor, faça uma pergunta sobre padrões gráficos, indicadores (como RSI/EMA) ou conceitos básicos de trading."

    return JSONResponse({"ok": True, "response": response_text})

