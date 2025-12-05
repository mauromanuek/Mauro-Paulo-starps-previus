# main.py (VERSÃO FINAL COM BOTS E IA)

import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
from datetime import datetime
from typing import Dict, Any

# Importações dos módulos Core
from deriv_client import DerivClient
from bots_manager import BotsManager
from strategy import TradingStrategy 

# Conteúdo dos e-books (para o IA Trader)
# Este conteúdo serve como base de conhecimento para responder às perguntas
EBOOK_CONTENT = """
--- CONTEÚDO EBOOK 1 (XP Investimentos) ---
SUMÁRIO: Introdução. Análise técnica e Teoria de Dow (Os preços descontam tudo, Mercados se movem em tendência, A tendência primária tem três fases). Tipos de gráficos (linhas, barras, candles). Períodos Gráficos (Escala logarítmica ou aritmética). Movimentos que geram tendências (Suporte e resistência, Tendência, Linhas de Tendências, Canais de Alta e Baixa).

--- CONTEÚDO EBOOK 2 (Clear Corretora) ---
Índice: Introdução. Gráficos. Escala dos gráficos. Indexação. Periodicidade. Teoria de Dow e seus princípios. Suportes e resistências. Tendências. As periodicidades das tendências conflitantes. Linha de tendência. Formações gráficas (padrões). Padrões de reversão. Candlesticks. Figuras de reversão (candlestick). Indicadores: OBV (On Balance Volume).
"""
# ****************************************************

# Inicialização Global
app = FastAPI(title="RobotMagic Pro")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Arquivos estáticos
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Instâncias globais do Core
global_strategy = TradingStrategy()
bots_manager = BotsManager()
deriv_client: DerivClient = None


# --------------------------------------
# ROTAS DE VIEW E MODELOS
# --------------------------------------
@app.get("/")
async def serve_index():
    return FileResponse("index.html")

class TokenModel(BaseModel):
    token: str

class BotSpec(BaseModel):
    name: str
    symbol: str
    tf: str
    stop_loss: float
    take_profit: float
    
class QueryModel(BaseModel):
    query: str


# --------------------------------------
# ROTAS DE CONEXÃO E SINAL
# --------------------------------------
@app.post("/set_token")
async def set_token(data: TokenModel):
    global deriv_client

    token = data.token.strip()
    if not token:
        return {"ok": False, "message": "Token vazio."}

    if deriv_client is not None:
        try:
            await deriv_client.stop()
        except:
            pass

    # Cria o cliente, passando a estratégia para receber ticks
    deriv_client = DerivClient(token, strategy_instance=global_strategy)
    asyncio.create_task(deriv_client.start())

    return {"ok": True, "message": "Token recebido. Conectando..."}

@app.get("/status")
async def status():
    ok = deriv_client is not None and deriv_client.connected
    
    return {
        "deriv_connected": ok,
        "balance": deriv_client.account_info["balance"] if deriv_client else 0.0,
        "account_type": deriv_client.account_info["account_type"] if deriv_client else "disconnected",
        "active_bots": bots_manager.list_bots(), 
    }

@app.get("/signal")
async def signal(symbol: str, tf: str):
    if deriv_client is None or not deriv_client.connected:
        raise HTTPException(status_code=400, detail="Deriv Client não está ativo ou conectado.")

    result = global_strategy.generate_signal(symbol, tf)

    if result.get("action") is None:
        raise HTTPException(status_code=404, detail="Não há dados suficientes ou a estratégia não gerou um sinal.")
    
    return result


# --------------------------------------
# ROTAS DE GESTÃO DE BOTS (PONTO 8)
# --------------------------------------
@app.post("/bots/create")
async def create_bot_route(spec: BotSpec):
    bot_id = bots_manager.create_bot(spec.model_dump())
    return {"ok": True, "id": bot_id}

@app.post("/bots/activate/{bot_id}")
async def activate_bot_route(bot_id: str):
    bot = bots_manager.activate_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot não encontrado.")
    return {"ok": True, "bot": bot}

@app.post("/bots/deactivate/{bot_id}")
async def deactivate_bot_route(bot_id: str):
    bot = bots_manager.deactivate_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot não encontrado.")
    return {"ok": True, "bot": bot}


# --------------------------------------
# ROTA IA TRADER (PONTO 9)
# --------------------------------------
@app.post("/ia/query")
async def ia_query_route(data: QueryModel):
    """Simula a consulta ao modelo de IA, baseada nos e-books."""
    query = data.query.lower()
    
    # Lógica de simulação de IA usando o EBOOK_CONTENT
    
    if "triângulo ascendente" in query or "formação gráfica" in query:
        response = "Um **Triângulo Ascendente** é um padrão gráfico de continuação ou reversão que sugere uma quebra de alta. É caracterizado por uma linha de resistência horizontal e uma linha de tendência de suporte ascendente. A Teoria de Dow indica que o volume deve confirmar a quebra."
    elif "rsi" in query or "sobrecompra" in query:
        response = "O **RSI (Índice de Força Relativa)** é um oscilador de momentum usado para medir a velocidade e mudança dos movimentos de preço. Níveis acima de 70 sugerem **Sobrecompra** e podem indicar uma reversão de baixa. Níveis abaixo de 30 sugerem **Sobrevenda** e podem indicar uma reversão de alta, conforme os princípios da Análise Técnica."
    elif "teoria de dow" in query:
        response = "A **Teoria de Dow** é a base da Análise Técnica. Seus seis princípios incluem: os preços descontam tudo; o mercado se move em tendências; a tendência primária tem três fases; o volume deve confirmar a tendência; a tendência precisa ser confirmada por dois índices; e uma tendência é válida até que haja um sinal claro de reversão."
    else:
        response = f"Atualmente, estou processando sua pergunta sobre '{query}'. Meu conhecimento está baseado em princípios de Análise Técnica (como Teoria de Dow, Suportes, Resistências e Candlesticks), conforme seus materiais de referência. Por favor, tente uma pergunta mais específica sobre esses tópicos."

    return {"ok": True, "response": response}


# --------------------------------------
# RUN UVICORN
# --------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
