# main.py - Versão FINAL E CORRIGIDA: CORS, Conexão Assíncrona e Sinal de Velas

import asyncio
import uuid
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json

# --- IMPORTS CORRIGIDOS ---
from fastapi.middleware.cors import CORSMiddleware 
# --------------------------

from strategy import generate_signal 
from deriv_client import DerivClient
from bots_manager import BotsManager, BotState 

# Variáveis globais
app = FastAPI()
client: Optional[DerivClient] = None
bots_manager: Optional[BotsManager] = None

# 🟢 CORREÇÃO 1: ADIÇÃO DO MIDDLEWARE CORS (Extremamente Permissivo para Teste) 🟢
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
# -------------------------------------------


# Montar pasta static para CSS e JS
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuração de templates
templates = Jinja2Templates(directory=".")

# --- Models Pydantic (inalteradas) ---
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
    """Carrega a página principal do dashboard."""
    return templates.TemplateResponse("index.html", {"request": request})


# --- 2. ROTA DE AUTORIZAÇÃO (POST) ---
@app.post("/set_token", response_class=JSONResponse)
async def set_token(data: TokenRequest):
    """Lida com a conexão e autorização do token da Deriv."""
    global client, bots_manager
    
    # 1. Parar cliente antigo (se existir)
    if client:
        await client.stop() 
        client = None

    # O DerivClient agora recebe o bots_manager OBRIGATORIAMENTE
    client = DerivClient(data.token, bots_manager) 
    
    try:
        # 🟢 CORREÇÃO 2: Inicia a conexão em TAREFA DE FUNDO 🟢
        # Isto é essencial para o FastAPI responder e evita o erro de timeout
        asyncio.create_task(client.connect_and_subscribe(symbol="R_100")) 

        # 2. Esperar pela autorização
        for _ in range(10): 
            if client.authorized: # O client.authorized agora existe garantidamente
                return JSONResponse({
                    "ok": True, 
                    "message": "Conectado e Autorizado. Dados de velas a carregar...",
                    "account_type": client.account_info.get("account_type"),
                    "balance": client.account_info.get("balance")
                })
            await asyncio.sleep(0.5)

        # Se o loop terminar sem autorização
        await client.stop()
        raise HTTPException(status_code=401, detail="Token inválido ou falha na autorização (Timeout).")
        
    except Exception as e:
        if client:
            await client.stop()
            client = None
        raise HTTPException(status_code=500, detail=f"Erro ao conectar: {str(e)}")


# --- 3. ROTA DE STATUS (GET) ---
@app.get("/status", response_class=JSONResponse)
async def get_status():
    """Retorna o status atual da conexão e saldo."""
    global client
    # 🚨 Linha onde estava o AttributeError 🚨:
    # A verificação 'client and' garante que não tentamos acessar o atributo se client for None.
    # Como o atributo 'authorized' agora é garantido no __init__ do DerivClient, o erro deve sumir.
    status = {
        "connected": client and client.connected, 
        "authorized": client and client.authorized, 
        "balance": client.account_info.get("balance", 0.0) if client else 0.0,
        "account_type": client.account_info.get("account_type", "offline") if client else "offline"
    }
    return JSONResponse(status)


# --- 4. ROTA DE SINAL (GET) ---
@app.get("/signal")
async def get_signal(symbol: str = "R_100"):
    """
    Gera um sinal de trading com base nos preços de fecho das velas de 1m.
    """
    if not client or not client.authorized:
        raise HTTPException(status_code=401, detail="Não autorizado. Faça o login primeiro.")
    
    # O tf (timeframe) é fixo em "1m"
    signal = generate_signal(symbol, "1m") 
        
    if signal is not None:
        return signal
    
    raise HTTPException(
        status_code=404, 
        detail=f"Os dados históricos (velas de 1m) ainda não foram completamente carregados. Tente novamente em 5 segundos."
    )


# --- 5. ROTAS DE GESTÃO DE BOTS ---
class BotAction(BaseModel):
    bot_id: str

@app.post("/bot/create", response_class=JSONResponse)
async def create_bot(data: BotCreationRequest):
    """Cria e inicia um novo bot de trading."""
    global bots_manager, client
    if not bots_manager or not client or not client.authorized:
        raise HTTPException(status_code=401, detail="Cliente não autorizado ou gestor de bots não inicializado.")

    new_bot = bots_manager.create_bot(data.name, data.symbol, data.tf, data.stop_loss, data.take_profit, client)

    new_bot.current_run_task = asyncio.create_task(new_bot.run_loop())
    
    return JSONResponse({"ok": True, "message": f"Bot '{data.name}' criado e iniciado.", "bot_id": new_bot.id})

@app.get("/bots/list", response_class=JSONResponse)
async def list_bots():
    """Lista todos os bots ativos."""
    global bots_manager
    if not bots_manager:
        return JSONResponse({"bots": []})
        
    bots_list = []
    for bot in bots_manager.get_all_bots():
        bots_list.append({
            "id": bot.id,
            "name": bot.name,
            "symbol": bot.symbol,
            "tf": bot.tf,
            "state": bot.state.value,
            "sl": bot.stop_loss,
            "tp": bot.take_profit,
        })
    return JSONResponse({"bots": bots_list})

@app.post("/bot/pause", response_class=JSONResponse)
async def pause_bot(data: BotAction):
    """Pausa um bot de trading existente."""
    global bots_manager
    bot = bots_manager.get_bot(data.bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot não encontrado.")
    bot.state = BotState.PAUSED
    return JSONResponse({"ok": True, "message": f"Bot {bot.name} pausado."})


# --- 6. ROTA DE CONSULTA DA IA ---
@app.post("/ia/query", response_class=JSONResponse)
async def ia_query(data: IAQueryRequest):
    """Processa consultas de análise técnica feitas ao módulo de IA."""
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


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
