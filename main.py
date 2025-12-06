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
import time # Adicionado para time.sleep na IA (simulação)

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
    """Carrega a página principal do dashboard/login."""
    return templates.TemplateResponse("index.html", {"request": request})


# --- 2. ROTAS DE AUTENTICAÇÃO E CONEXÃO ---

# Rota /api/connect (CORRIGIDA)
@app.post("/api/connect") 
async def connect(data: TokenRequest):
    """Cria e inicia o cliente Deriv usando o token API, e inicia os bots se a conexão for bem-sucedida."""
    global client
    global bots_manager
    
    # 🚨 CORREÇÃO CRÍTICA: Se já existe um cliente conectado e autorizado, evita recriação.
    if client and client.connected and client.authorized:
        return JSONResponse({"ok": True, "message": "Cliente já está conectado e autorizado."}, status_code=200)

    try:
        # Se um cliente anterior existir (mesmo desconectado), paramos ele para limpeza.
        if client:
            await client.stop()
        
        # Cria e inicia o novo cliente (AGORA ESPERA-SE PELA CONEXÃO)
        client = DerivClient(data.token)
        # O start() agora deve ser await, pois a lógica de autorização está dentro dele.
        await client.start() 

        if client.authorized:
            # 🚨 CRÍTICO: Iniciar o loop de bots após a autorização.
            # (Requer que a função start_all_bots seja implementada no BotsManager)
            if bots_manager:
                bots_manager.start_all_bots() 
            
            return JSONResponse({"ok": True, "message": "Conexão e autorização bem-sucedidas. Bots iniciados."}, status_code=200)
        else:
            await client.stop()
            return JSONResponse({"ok": False, "message": "Autorização falhou. Verifique o Token API."}, status_code=401)

    except Exception as e:
        if client:
            await client.stop()
        print(f"[ERRO GERAL CONEXÃO] {e}")
        # Retorna erro 500 para o frontend
        raise HTTPException(status_code=500, detail=f"Erro de servidor durante a conexão: {e}")


# Rota /api/status (CORRIGIDA)
@app.get("/api/status")
async def get_status():
    """Retorna o status atual da conexão, conta e lista de bots."""
    global client
    global bots_manager
    
    # 1. Obter informações básicas
    connected = client is not None and client.connected
    authorized = client is not None and client.authorized
    
    # 2. Obter dados da conta (garante que as chaves existam mesmo que o cliente não esteja totalmente pronto)
    account_info = {
        # Acesso seguro a account_info
        "balance": client.account_info.get("balance", 0.0) if client and client.account_info else 0.0,
        "account_type": client.account_info.get("account_type", "OFFLINE") if client and client.account_info else "OFFLINE",
        "currency": client.account_info.get("currency", "USD") if client and client.account_info else "USD",
        "account_name": client.account_info.get("account_name", "N/A") if client and client.account_info else "N/A",
    }

    # 3. Obter status dos bots
    bot_list = []
    if bots_manager:
        for bot in bots_manager.get_all_bots():
            # Estrutura completa para o frontend
            bot_list.append({
                "id": bot.id, 
                "name": bot.name, 
                "symbol": bot.symbol,
                "tf": bot.tf, 
                "stop_loss": bot.stop_loss, 
                "take_profit": bot.take_profit, 
                "state": bot.state.value
            })

    return JSONResponse({
        "ok": connected and authorized,
        "connected": connected,
        "authorized": authorized,
        "account_info": account_info,
        "bots": bot_list
    })


# --- 3. ROTA DE SINAL (ANÁLISE) ---

@app.get("/api/signal") # CORRIGIDA
async def get_signal(symbol: str, tf: str):
    """
    Gera e retorna um sinal de trading com base na análise dos ticks.
    """
    if not client or not client.authorized:
        raise HTTPException(status_code=401, detail="Não autorizado. Faça o login primeiro.")
    
    signal = generate_signal(symbol, tf)
    
    if signal is None:
        raise HTTPException(status_code=404, detail="Não há dados suficientes para gerar o sinal (requer 20 ticks).")
    
    return signal


# --- 4. ROTAS DE BOTS AUTOMÁTICOS ---

@app.post("/api/bots") # CORRIGIDA
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
    
    # Inicia a tarefa do bot em segundo plano, se o estado padrão for ACTIVE
    if bot.is_active:
        asyncio.create_task(bot.run_bot_loop())
    
    return JSONResponse({"ok": True, "bot_id": bot.id, "message": f"Bot '{data.name}' criado e iniciado."})


@app.post("/api/bots/activate/{bot_id}") # CORRIGIDA
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
    # CRÍTICO: Reinicia o loop do bot quando ativado.
    asyncio.create_task(bot.run_bot_loop()) 
    return JSONResponse({"ok": True, "message": f"Bot ID {bot_id} ativado."})


@app.post("/api/bots/deactivate/{bot_id}") # CORRIGIDA
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
    
    # CRÍTICO: O loop do bot irá terminar sozinho na próxima verificação de estado.
    bot.state = BotState.INACTIVE 
    return JSONResponse({"ok": True, "message": f"Bot ID {bot_id} desativado."})


# --- 5. ROTA DE IA TRADER ---

@app.post("/api/ia/query") # CORRIGIDA
async def ia_query(data: IAQueryRequest):
    """Simula uma resposta de IA para perguntas de trading."""
    # Simulação: Em um projeto real, aqui você usaria um modelo de LLM (como Gemini, GPT)
    
    # Simulação de latência de IA
    await asyncio.sleep(1) 
    
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
