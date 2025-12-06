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
# Importa as funções da estratégia, agora incluindo 'calculate_indicators'
from strategy import generate_signal, calculate_indicators 
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
    """Carrega a página principal do dashboard ou a tela de login."""
    global client
    
    context = {
        "request": request,
        "is_connected": client is not None and client.connected,
        "is_authorized": client is not None and client.authorized,
        "balance": client.account_info["balance"] if client else 0.0,
        "account_type": client.account_info["account_type"] if client else "demo",
        # 🟢 CORREÇÃO DA LINHA 64: De get_all_bots() para get_all_bots_info()
        "bots": bots_manager.get_all_bots_info() if bots_manager else [] 
    }
    
    return templates.TemplateResponse("index.html", context)


# --- 2. ROTA DE STATUS DA CONEXÃO ---
@app.get("/status", response_class=JSONResponse)
async def get_status():
    """Retorna o status atual da conexão com a Deriv e o saldo."""
    global client
    
    if client is None or not client.connected:
        return JSONResponse({"ok": False, "status": "DISCONNECTED", "balance": 0.0, "account_type": "demo"})
    
    return JSONResponse({
        "ok": True, 
        "status": "CONNECTED" if client.authorized else "AUTHORIZING",
        "balance": client.account_info.get("balance", 0.0),
        "account_type": client.account_info.get("account_type", "demo")
    })

# --- 3. ROTA DE AUTENTICAÇÃO (TOKEN) ---
@app.post("/set_token", response_class=JSONResponse)
async def set_token(data: TokenRequest):
    """Define o token da Deriv e inicia a conexão."""
    global client
    
    # 1. Parar cliente antigo se existir
    if client and client.connected:
        await client.stop()
        
    # 2. Criar e iniciar novo cliente
    client = DerivClient(data.token)
    await client.start()

    if client.authorized:
        return JSONResponse({"ok": True, "message": "Conectado e Autorizado com sucesso."})
    else:
        # Se a autorização falhar, o cliente pára automaticamente
        raise HTTPException(status_code=401, detail="Token inválido ou falha na conexão.")


# --- 4. ROTA DE SINAL DE TRADING (A CORREÇÃO NECESSÁRIA) ---
@app.get("/signal/{symbol}", response_class=JSONResponse)
async def get_signal_for_asset(symbol: str):
    """
    Rota que retorna o sinal de trading (CALL/PUT) para um ativo,
    baseado nos indicadores mais recentes.
    """
    global client
    
    # Verifica se há conexão antes de prosseguir
    if client is None or not client.connected or not client.authorized:
        return JSONResponse({
            "ok": False, 
            "signal": "NONE", 
            "reason": "Cliente Deriv não está conectado ou autorizado.",
            "explanation": "Conecte-se e autorize o token primeiro."
        }, status_code=400) # 400 Bad Request

    # 1. Obtém os indicadores (RSI, EMA)
    indicators = calculate_indicators()
    
    # Verifica se há dados suficientes para calcular
    if not indicators:
        return JSONResponse({
            "ok": False, 
            "signal": "NONE", 
            "reason": "Aguardando dados suficientes (ticks) para calcular os indicadores.",
            "explanation": "São necessários 20 ticks para a estratégia começar a funcionar."
        })

    # 2. Gera o sinal com a lógica de trading (função de strategy.py)
    signal_data = generate_signal(indicators) 
    
    if signal_data:
        # Retorna um sinal de trading
        return JSONResponse({
            "ok": True, 
            "symbol": symbol,
            "signal": signal_data["action"], # CALL ou PUT
            "reason": signal_data["reason"],
            "explanation": signal_data.get("explanation", "Sinal gerado.")
        })
    else:
        # Não há sinal forte no momento (generate_signal retornou None)
        return JSONResponse({
            "ok": False, 
            "signal": "NONE", 
            "reason": "Aguardando formação de sinal forte pela estratégia.",
            "explanation": "Os indicadores estão numa zona neutra."
        })


# --- 5. ROTA DE CRIAÇÃO DE BOT ---
@app.post("/create_bot", response_class=JSONResponse)
async def create_bot(data: BotCreationRequest):
    """Cria e inicia um novo bot de trading."""
    global bots_manager, client

    if client is None or not client.authorized:
        raise HTTPException(status_code=400, detail="Conecte-se e autorize o token primeiro.")
    
    bot = bots_manager.create_bot(
        name=data.name,
        symbol=data.symbol,
        tf=data.tf,
        stop_loss=data.stop_loss,
        take_profit=data.take_profit,
        client=client
    )
    # Inicia o loop de trading do bot em uma tarefa em background
    bot.start() 

    return JSONResponse({"ok": True, "message": f"Bot '{bot.name}' criado e iniciado com sucesso.", "bot_id": bot.id})


# --- 6. ROTA DA IA (CHATBOT) ---
class IAQueryResponse(BaseModel):
    ok: bool
    response: str

@app.post("/ia/query", response_model=IAQueryResponse)
async def ia_query(data: IAQueryRequest):
    """Processa a query do usuário e retorna uma análise técnica da IA."""
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
    
