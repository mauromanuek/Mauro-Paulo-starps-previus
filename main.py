# main.py - VERSÃO FINAL CORRIGIDA

import asyncio
import uuid
from fastapi import FastAPI, Request, HTTPException, Query # Query é essencial para o login funcionar
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
from fastapi.responses import HTMLResponse # Essencial para servir o index.html

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
    return templates.TemplateResponse("index.html", {"request": request}) 


# --- 2. ROTA CRÍTICA: SET TOKEN (CORRIGIDA COM QUERY PARAMETER) ---
@app.post("/set_token")
async def set_token_and_start_client(token: str = Query(..., description="O Token API da Deriv")):
    """
    Recebe o token API como um parâmetro de query (Query Parameter) e inicia o cliente Deriv.
    """
    global client
    
    if client and client.connected:
        raise HTTPException(status_code=400, detail="O cliente já está conectado. Desconecte primeiro.")

    # 1. Cria e inicia o cliente Deriv
    client = DerivClient(token=token)
    
    # Executa a função start em segundo plano para não bloquear a resposta HTTP
    asyncio.create_task(client.start())
    
    # Retorna uma resposta imediata de sucesso
    return JSONResponse({"ok": True, "message": "Cliente Deriv a iniciar a conexão."})


# --- 3. ROTA DE STATUS ---
@app.get("/status")
async def get_status():
    """Retorna o status da conexão, saldo e bots ativos."""
    is_authorized = client.authorized if client else False
    balance = client.account_info.get("balance", 0.0) if client else 0.0
    account_type = client.account_info.get("account_type", "demo") if client else "demo"
    
    # Busca a lista de bots para enviar ao frontend
    active_bots_data = []
    if bots_manager:
        for bot in bots_manager.get_all_bots():
            active_bots_data.append({
                "id": bot.id,
                "name": bot.name,
                "symbol": bot.symbol,
                "tf": bot.tf,
                "stop_loss": bot.stop_loss,
                "take_profit": bot.take_profit,
                "is_active": bot.is_active
            })

    return JSONResponse({
        "is_authorized": is_authorized,
        "balance": balance,
        "account_type": account_type,
        "active_bots": active_bots_data
    })


# --- 4. ROTA DE SINAL (ANÁLISE MANUAL) ---
@app.get("/signal")
async def get_trading_signal(symbol: str, tf: str):
    """Gera um sinal de trading com base nos dados mais recentes."""
    
    if not client or not client.authorized:
        raise HTTPException(status_code=401, detail="Não Autorizado. Conecte o Token API primeiro.")

    # Usa a função de estratégia
    signal_data = generate_signal()

    if not signal_data:
        # Retorna 404 se não houver dados suficientes para análise (ex: menos de 20 ticks)
        raise HTTPException(status_code=404, detail="Dados insuficientes para gerar um sinal (mínimo 20 ticks). Aguardando mais dados.")
    
    # Adiciona metadados ao sinal
    signal_data["symbol"] = symbol
    signal_data["tf"] = tf
    
    return JSONResponse(signal_data)


# --- 5. ROTAS DE GESTÃO DE BOTS ---

# LINHA 132 (Agora corrigida)
@app.post("/bots/create")
async def create_new_bot(data: BotCreationRequest):
    """Cria, registra e inicia o loop de um novo bot de trading."""
    global client, bots_manager
    if not client or not client.authorized:
        raise HTTPException(status_code=401, detail="Não Autorizado. Conecte o Token API primeiro.")
    
    if not bots_manager:
        raise HTTPException(status_code=500, detail="O Gestor de Bots não está inicializado.")

    bot = bots_manager.create_bot(
        name=data.name,
        symbol=data.symbol,
        tf=data.tf,
        stop_loss=data.stop_loss,
        take_profit=data.take_profit,
        client=client # Passa a instância do cliente Deriv para o bot
    )
    
    # Inicia a tarefa do bot em segundo plano
    bot.state = BotState.ACTIVE
    bot.current_run_task = asyncio.create_task(bot.run_loop())
    
    return JSONResponse({"ok": True, "bot_id": bot.id, "message": f"Bot {bot.name} criado e iniciado."})


@app.post("/bots/activate/{bot_id}")
async def activate_bot_endpoint(bot_id: str):
    """Ativa um bot existente e reinicia seu loop se necessário."""
    bot = bots_manager.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot não encontrado.")
    
    if not bot.is_active:
        bot.state = BotState.ACTIVE
        # Se não houver tarefa de execução, reinicia o loop
        if not bot.current_run_task or bot.current_run_task.done():
            bot.current_run_task = asyncio.create_task(bot.run_loop())
            
    return JSONResponse({"ok": True, "message": f"Bot {bot.id[:4]} ativado."})

@app.post("/bots/deactivate/{bot_id}")
async def deactivate_bot_endpoint(bot_id: str):
    """Desativa um bot existente e cancela seu loop de execução."""
    bot = bots_manager.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot não encontrado.")
    
    bot.state = BotState.INACTIVE
    
    # Tenta cancelar a tarefa em execução
    if bot.current_run_task and not bot.current_run_task.done():
        bot.current_run_task.cancel()
    
    return JSONResponse({"ok": True, "message": f"Bot {bot.id[:4]} desativado."})


# --- 6. ROTA DE CONSULTA IA ---
@app.post("/ia/query")
async def ia_query(data: IAQueryRequest):
    """Simula uma consulta a uma IA de análise técnica."""
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
