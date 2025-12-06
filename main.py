# main.py

import asyncio
import uuid
# 🚨 CRÍTICO: Adicionar 'WebSocket' ao import
from fastapi import FastAPI, Request, HTTPException, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
import websockets # Necessário para tratar a exceção websockets.exceptions.ConnectionClosedOK

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


# --- EVENTOS DE INICIALIZAÇÃO ---
@app.on_event("startup")
async def startup_event():
    """Função executada ao iniciar o servidor."""
    global bots_manager
    bots_manager = BotsManager()
    print("✅ BotsManager inicializado.")

# --- 1. ROTA PRINCIPAL (INDEX) ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Carrega a página principal do frontend."""
    return templates.TemplateResponse("index.html", {"request": request})

# ----------------------------------------------------------------------
# --- 2. ROTA DE CONEXÃO E AUTORIZAÇÃO (API) ---
# ----------------------------------------------------------------------
@app.post("/api/connect")
async def connect_client(data: TokenRequest):
    global client
    
    # 1. Limpa a conexão antiga
    if client and client.connected:
        await client.stop()
    
    try:
        # 2. Inicia a nova conexão e autorização
        client = DerivClient(token=data.token)
        await client.start()
        
        # 3. VERIFICAÇÃO CRÍTICA DO ESTADO FINAL
        if client.authorized:
            if bots_manager:
                # O start_all_bots inicia os loops de trade (bots_manager.py)
                bots_manager.start_all_bots() 
                
            # NOVO: Inclui o último preço conhecido (se houver) na resposta inicial
            last_price = client.account_info.get('last_price', 'N/A')
            
            response_data = {
                "ok": True, 
                "message": "Conectado com sucesso", 
                "account_info": client.account_info,
                "last_price": last_price
            }
            return JSONResponse(response_data)
        else:
            # Token inválido ou falha de autorização
            await client.stop()
            raise HTTPException(status_code=401, detail="Falha na autorização. Verifique o token ou a conexão.")

    except HTTPException as e:
        raise e
    except Exception as e:
        if client: await client.stop()
        print(f"[ERRO] Erro grave na conexão: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ou timeout ao tentar conectar ao Deriv.")

# ----------------------------------------------------------------------
# --- 3. ROTAS DE GESTÃO DE BOTS ---
# ----------------------------------------------------------------------

@app.post("/api/bots/create")
async def create_bot(data: BotCreationRequest):
    if not client or not client.authorized:
        raise HTTPException(status_code=401, detail="Cliente não autorizado.")
    
    if bots_manager is None:
        raise HTTPException(status_code=500, detail="Bots Manager não inicializado.")

    if data.symbol != "R_100":
         raise HTTPException(status_code=400, detail="Apenas o ativo R_100 é suportado nesta versão.")

    new_bot = bots_manager.create_bot(
        name=data.name,
        symbol=data.symbol,
        tf=data.tf,
        stop_loss=data.stop_loss,
        take_profit=data.take_profit,
        client=client
    )
    
    new_bot.start_loop()

    return JSONResponse({
        "ok": True,
        "message": f"Bot '{new_bot.name}' criado e ativo.",
        "bot": {
            "id": new_bot.id,
            "name": new_bot.name,
            "symbol": new_bot.symbol,
            "state": new_bot.state.value
        }
    })

@app.get("/api/bots")
async def get_bots():
    if bots_manager is None:
        return JSONResponse({"ok": True, "bots": []})
    
    bots_list = [
        {
            "id": bot.id, 
            "name": bot.name, 
            "symbol": bot.symbol, 
            "tf": bot.tf,
            "state": bot.state.value, 
            "sl": bot.stop_loss,
            "tp": bot.take_profit
        } for bot in bots_manager.get_all_bots()
    ]
    return JSONResponse({"ok": True, "bots": bots_list})


@app.post("/api/bots/{bot_id}/action")
async def bot_action(bot_id: str, action: Dict[str, str]):
    if bots_manager is None:
        raise HTTPException(status_code=500, detail="Bots Manager não inicializado.")
    
    bot = bots_manager.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot não encontrado.")
    
    action_type = action.get("action", "").upper()
    
    if action_type == "START" or action_type == "ACTIVATE":
        bot.state = BotState.ACTIVE
        if client and client.authorized:
            bot.start_loop() 
        return JSONResponse({"ok": True, "message": f"Bot {bot.id[:4]} iniciado."})
        
    elif action_type == "STOP" or action_type == "PAUSE":
        bot.state = BotState.PAUSED
        if bot.current_run_task:
            bot.current_run_task.cancel()
        return JSONResponse({"ok": True, "message": f"Bot {bot.id[:4]} pausado."})
        
    elif action_type == "DELETE":
        bot.state = BotState.INACTIVE 
        if bot.current_run_task:
            bot.current_run_task.cancel()
        del bots_manager.active_bots[bot_id]
        return JSONResponse({"ok": True, "message": f"Bot {bot.id[:4]} excluído."})
        
    else:
        raise HTTPException(status_code=400, detail="Ação inválida.")


# ----------------------------------------------------------------------
# --- 4. ROTA WEBSOCKET PARA ATUALIZAÇÃO DE TICKS (FRONT-END) ---
# ----------------------------------------------------------------------

@app.websocket("/ws/ticks")
async def websocket_endpoint(websocket: WebSocket):
    global client
    
    if not client or not client.authorized:
        # Se não estiver autorizado, fecha a conexão WebSocket imediatamente
        await websocket.close(code=1008, reason="Cliente Deriv não autorizado.")
        return

    # Cria uma queue exclusiva para este cliente WebSocket
    queue = asyncio.Queue()
    
    # Adiciona a queue à lista de listeners do DerivClient
    await client.subscribe_tick_listener(queue)
    
    await websocket.accept()
    print(f"[WS] Novo cliente de ticks conectado: {websocket.client}")

    try:
        # Loop para enviar ticks do DerivClient para o Front-end
        while True:
            # Espera por uma mensagem na queue (tick)
            message = await queue.get()
            
            # Envia o tick para o cliente WebSocket
            await websocket.send_text(message) 
            
    except websockets.exceptions.ConnectionClosedOK:
        # Conexão fechada pelo cliente (navegador)
        print(f"[WS] Cliente de ticks desconectado normalmente: {websocket.client}")
    except Exception as e:
        print(f"[WS] Erro na conexão WebSocket do cliente: {e}")
    finally:
        # CRÍTICO: Remove a queue da lista de listeners ao desconectar
        client.unsubscribe_tick_listener(queue)
        print(f"[WS] Cliente de ticks desconectado. Listener removido.")


# ----------------------------------------------------------------------
# --- 5. ROTA DA IA TRADER (Simulação) ---
# ----------------------------------------------------------------------

@app.post("/ia/query")
async def ia_query(data: IAQueryRequest):
    query = data.query.lower()

    if "triângulo ascendente" in query:
        response_text = "O Triângulo Ascendente é um padrão de continuação bullish. É formado por uma linha de resistência horizontal no topo e uma linha de suporte ascendente na base. Sugere que os compradores estão a ganhar força e que uma quebra acima da resistência é provável."
    elif "rsi" in query or "sobrecompra" in query:
        response_text = "O Índice de Força Relativa (RSI) mede a velocidade e a mudança dos movimentos de preço. Um RSI acima de 70 indica **sobrecompra** (potencial de queda), e um abaixo de 30 indica **sobrevenda** (potencial de subida)."
    elif "suporte e resistência" in query:
        response_text = "Suporte e Resistência são níveis de preço cruciais onde a pressão de compra ou venda historicamente se concentra. O suporte é um 'piso' onde o preço tende a subir, e a resistência é um 'teto' onde o preço tende a cair."
    elif "bitcoin" in query or "binance" in query:
        response_text = "A análise técnica se aplica a qualquer mercado, incluindo criptomoedas como Bitcoin. No entanto, a alta volatilidade exige cautela e stop-loss mais rígidos."
    else:
        response_text = "Desculpe, a minha base de dados de análise técnica está limitada. Por favor, faça uma pergunta sobre padrões gráficos, indicadores (como RSI/EMA) ou conceitos básicos de trading."

    return JSONResponse({"ok": True, "response": response_text})
