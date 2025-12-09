# main.py - Versão FINAL E COMPLETA: CORS, Timeout de 20s, e Todas as Rotas

import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json

from fastapi.middleware.cors import CORSMiddleware 

from strategy import generate_signal, MIN_TICKS_REQUIRED 
from deriv_client import DerivClient
from bots_manager import BotsManager, BotState 

# Variáveis globais
app = FastAPI()
client: Optional[DerivClient] = None
bots_manager: Optional[BotsManager] = None

# --- CONFIGURAÇÃO CORS ---
origins = ["*"] 
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)
# --------------------------

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

class BotAction(BaseModel):
    bot_id: str

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


# --- 2. ROTA DE AUTORIZAÇÃO (POST) - CRÍTICO: ESPERA 20s ---
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

        # 2. Esperar pela autorização E carregamento de histórico (40 tentativas * 0.5s = 20 segundos)
        for _ in range(40): # 👈 O loop de espera
            
            # Condição de Sucesso: Autorizado E Histórico Carregado
            if client.authorized and client.history_loaded:
                return JSONResponse({
                    "ok": True, 
                    "message": "Conectado, Autorizado e Histórico de Velas Carregado. O bot está PRONTO.",
                    "account_type": client.account_info.get("account_type"),
                    "balance": client.account_info.get("balance")
                })
            
            # Condição de Falha Imediata (Token realmente inválido)
            if not client.is_connected and not client.authorized and client.ws is None:
                 await client.stop()
                 raise HTTPException(status_code=401, detail="Conexão Falhou: Token inválido, expirado ou problema de rede (veja o log do servidor).")
            
            await asyncio.sleep(0.5)

        # Timeout (Chegou ao fim do loop sem sucesso)
        await client.stop()
        raise HTTPException(status_code=401, detail="Token inválido, falha na autorização ou o histórico de velas não carregou a tempo (Timeout de 20s).")
        
    except HTTPException as e:
        raise e
    except Exception as e:
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
        "data_ready": client and client.authorized and client.history_loaded,
        "balance": client.account_info.get("balance", 0.0) if client else 0.0,
        "account_type": client.account_info.get("account_type", "offline") if client else "offline"
    }
    return JSONResponse(status)


# --- 4. ROTA DE SINAL (GET) ---
@app.get("/signal")
async def get_signal(symbol: str = "R_100"):
    # Garante que o bot só analisa se houver dados prontos
    if not client or not (client.authorized and client.history_loaded):
        raise HTTPException(status_code=404, detail="Não autorizado ou Histórico de Velas ainda não carregado. Aguarde e tente novamente.")
    
    signal = generate_signal(symbol, "1m") 
        
    if signal is not None:
        return signal
    
    raise HTTPException(
        status_code=404, 
        detail=f"Não há dados suficientes para calcular todos os indicadores ({MIN_TICKS_REQUIRED} mínimos)."
    )

# --- 5. ROTAS DE GESTÃO DE BOTS ---

@app.post("/bot/create", response_class=JSONResponse)
async def create_bot(data: BotCreationRequest):
    global bots_manager, client
    if not bots_manager or not client or not client.authorized:
        raise HTTPException(status_code=401, detail="Cliente não autorizado ou gestor de bots não inicializado.")

    new_bot = bots_manager.create_bot(data.name, data.symbol, data.tf, data.stop_loss, data.take_profit, client)

    new_bot.current_run_task = asyncio.create_task(new_bot.run_loop())
    
    return JSONResponse({"ok": True, "message": f"Bot '{data.name}' criado e iniciado.", "bot_id": new_bot.id})

@app.get("/bots/list", response_class=JSONResponse)
async def list_bots():
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
    global bots_manager
    bot = bots_manager.get_bot(data.bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot não encontrado.")
    bot.state = BotState.PAUSED
    if bot.current_run_task:
        bot.current_run_task.cancel() 
    return JSONResponse({"ok": True, "message": f"Bot {bot.name} pausado."})

@app.post("/bot/start", response_class=JSONResponse)
async def start_bot(data: BotAction):
    global bots_manager
    bot = bots_manager.get_bot(data.bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot não encontrado.")
    
    if bot.state != BotState.RUNNING:
        if bot.current_run_task and not bot.current_run_task.done():
             bot.current_run_task.cancel()
        
        bot.state = BotState.RUNNING
        bot.current_run_task = asyncio.create_task(bot.run_loop())
    
    return JSONResponse({"ok": True, "message": f"Bot {bot.name} iniciado."})


# --- 6. ROTA DE CONSULTA DA IA ---
@app.post("/ia/query", response_class=JSONResponse)
async def ia_query(data: IAQueryRequest):
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
