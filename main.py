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
import os # Adicionado para boas práticas

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


# --- EVENTOS DE INICIALIZAÇÃO E FECHO ---

@app.on_event("startup")
async def startup_event():
    """Função executada ao iniciar o servidor."""
    global bots_manager
    bots_manager = BotsManager()
    print("✅ BotsManager inicializado.")

@app.on_event("shutdown")
async def shutdown_event():
    """Função executada ao desligar o servidor (CRÍTICO para fechar conexões)."""
    global client, bots_manager
    if bots_manager:
        # Para os loops de todos os bots
        bots_manager.stop_all_bots()
    if client and client.connected:
        # Fecha a conexão WebSocket
        await client.stop()
    print("🔴 Servidor desligado. Conexões fechadas.")


# --- 1. ROTA PRINCIPAL (INDEX) ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Carrega a página principal do index.html."""
    return templates.TemplateResponse("index.html", {"request": request})


# --- 2. ROTAS DE COMUNICAÇÃO DO CLIENTE ---

@app.post("/api/connect")
async def connect_client(data: TokenRequest):
    """Lida com a requisição de token API para conectar e autorizar."""
    global client
    
    # 1. Parar Cliente Antigo: Se já houver um cliente ativo, paramos os loops
    if client and client.connected:
        # Paramos os loops de todos os bots antes de fechar o cliente antigo
        bots_manager.stop_all_bots() 
        await client.stop() 
        
    client = DerivClient(token=data.token)
    
    # 2. Tenta iniciar a conexão WebSocket e autorizar
    try:
        await client.start()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar conexão: {e}")

    if not client.authorized:
        await client.stop()
        raise HTTPException(status_code=401, detail="Token API inválido. Verifique o seu token.")

    # 3. ATIVAÇÃO CRÍTICA DO BOT: Inicia o loop de execução para todos os bots
    active_bots = bots_manager.get_all_bots()
    if active_bots:
        for bot in active_bots:
            # 🎯 CHAMADA CRÍTICA: Inicia a tarefa assíncrona do bot
            bot.start_loop() 

    # 4. Retorna o sucesso e os dados da conta
    return JSONResponse({
        "ok": True,
        "message": f"Conectado e autorizado com sucesso!",
        "account_info": client.account_info
    })

# --- 3. OUTRAS ROTAS ---

@app.get("/api/status")
async def get_status():
    """Retorna o estado atual do cliente e dos bots."""
    
    # ... (Seu código original da rota /api/status) ...
    # Exemplo: Retorna o status da conexão
    status = {
        "connected": client is not None and client.connected,
        "authorized": client is not None and client.authorized,
        "balance": client.account_info.get("balance") if client else 0.0,
        "account_type": client.account_info.get("account_type") if client else "OFFLINE",
        "last_price": client.last_price if client else 0.0,
        "bots": [
            {"id": bot.id, "name": bot.name, "state": bot.state.value} 
            for bot in bots_manager.get_all_bots()
        ] if bots_manager else []
    }
    return JSONResponse(status)


@app.post("/api/bots")
async def create_bot(data: BotCreationRequest):
    """Cria e registra um novo bot."""
    global client
    if not client or not client.authorized:
         raise HTTPException(status_code=400, detail="Conecte-se e autorize o cliente Deriv primeiro.")
         
    new_bot = bots_manager.create_bot(
        name=data.name, 
        symbol=data.symbol, 
        tf=data.tf, 
        stop_loss=data.stop_loss, 
        take_profit=data.take_profit, 
        client=client
    )
    
    # Se o cliente estiver ativo, inicia o loop imediatamente para o novo bot
    if client.authorized:
        new_bot.start_loop()
        
    return JSONResponse({
        "ok": True, 
        "message": f"Bot '{data.name}' criado e iniciado.", 
        "bot_id": new_bot.id
    })


@app.post("/ia/query")
async def ia_query(data: IAQueryRequest):
    """Consulta o Trader IA."""
    
    query = data.query.lower()

    if "triângulo ascendente" in query:
        response_text = "O Triângulo Ascendente é um padrão de continuação bullish. É formado por uma linha de resistência horizontal no topo e uma linha de suporte ascendente na base. Sugere que os compradores estão a ganhar força e que uma quebra acima da resistência é provável."
    elif "rsi" in query or "sobrecompra" in query:
        response_text = "O Índice de Força Relativa (RSI) mede a velocidade e a mudança dos movimentos de preço. Um RSI acima de 70 indica sobrecompra (potencial de queda), e um abaixo de 30 indica sobrevenda (potencial de subida)."
    elif "suporte e resistência" in query:
        response_text = "Suporte e Resistência são níveis de preço cruciais onde a pressão de compra ou venda historicamente se concentra. O suporte é um 'piso' onde o preço tende a subir, e a resistência é um 'teto' onde o preço tende a cair."
    elif "bitcoin" in query or "binance" in query:
        response_text = "A análise técnica se aplica a qualquer mercado, incluindo criptomoedas como Bitcoin. No entanto, a alta volatilidade exige cautela e stop-loss mais rígidos."
    else:
        response_text = "Desculpe, a minha base de dados de análise técnica está limitada. Por favor, faça uma pergunta sobre padrões gráficos, indicadores (como RSI/EMA) ou conceitos básicos de trading."

    return JSONResponse({"ok": True, "response": response_text})
