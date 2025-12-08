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
    """Carrega a página principal do dashboard."""
    return templates.TemplateResponse("index.html", {"request": request})


# --- 2. ROTA DE AUTORIZAÇÃO (POST) ---
@app.post("/set_token", response_class=JSONResponse)
async def set_token(data: TokenRequest):
    """Lida com a conexão e autorização do token da Deriv."""
    global client
    if client:
        await client.stop() 
        client = None

    client = DerivClient(data.token)
    try:
        await client.start()
        if client.authorized:
            return JSONResponse({
                "ok": True, 
                "message": "Conectado e Autorizado.",
                "account_type": client.account_info.get("account_type"),
                "balance": client.account_info.get("balance")
            })
        else:
            await client.stop()
            raise HTTPException(status_code=401, detail="Token inválido ou falha na autorização.")
    except Exception as e:
        if client:
            await client.stop()
            client = None
        raise HTTPException(status_code=500, detail=f"Erro ao conectar: {e}")


# --- 3. ROTA DE STATUS (GET) ---
@app.get("/status", response_class=JSONResponse)
async def get_status():
    """Retorna o status atual da conexão e saldo."""
    global client
    status = {
        "connected": client and client.connected,
        "authorized": client and client.authorized,
        "balance": client.account_info.get("balance", 0.0) if client else 0.0,
        "account_type": client.account_info.get("account_type", "offline") if client else "offline"
    }
    return JSONResponse(status)


# --- 4. ROTA DE SINAL (GET) - 🟢 CORREÇÃO CRÍTICA DO TIMEOUT (30 SEGUNDOS) 🟢 ---
@app.get("/signal")
async def get_signal(symbol: str = "R_100", tf: str = "TICK"):
    """
    Tenta gerar um sinal de trading, repetindo por 30 segundos para acumular ticks.
    """
    if not client or not client.authorized:
        raise HTTPException(status_code=401, detail="Não autorizado. Faça o login primeiro.")
    
    # Tentaremos 180 vezes * 0.5s = 30 segundos de espera total (necessário para o R_100)
    MAX_ATTEMPTS = 120 
    
    for attempt in range(MAX_ATTEMPTS):
        # Tenta gerar o sinal (strategy.py retorna None se faltarem dados ou houver NaN)
        signal = generate_signal(symbol, tf) 
        
        if signal is not None:
            # Sucesso: Sinal gerado
            print(f"[Main] ✅ Sinal gerado após {attempt + 1} tentativas (tempo de espera: {attempt * 0.5}s).")
            return signal
        
        # Espera 0.5s e tenta novamente
        await asyncio.sleep(0.5) 
        
    # Falha Total: Após 90 segundos
    raise HTTPException(
        status_code=404, 
        detail=f"Não foi possível gerar o sinal após 90 segundos. O ativo ({symbol}) está a enviar ticks muito lentamente ou o cálculo falhou permanentemente. Verifique os logs."
    )


# --- 5. ROTAS DE GESTÃO DE BOTS ---

# Note: Esta é uma classe auxiliar que o Pydantic espera. O seu bots_manager.py deve ter a TradingBot
class BotAction(BaseModel):
    bot_id: str

@app.post("/bot/create", response_class=JSONResponse)
async def create_bot(data: BotCreationRequest):
    """Cria e inicia um novo bot de trading."""
    global bots_manager, client
    if not bots_manager or not client or not client.authorized:
        raise HTTPException(status_code=401, detail="Cliente não autorizado ou gestor de bots não inicializado.")

    new_bot = bots_manager.create_bot(data.name, data.symbol, data.tf, data.stop_loss, data.take_profit, client)

    # Inicia a tarefa assíncrona do bot
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
        # Excluir referências não serializáveis
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
