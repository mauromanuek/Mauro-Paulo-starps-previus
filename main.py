# main.py
import os
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
import time

from deriv_client import DerivClient
import strategy  # generate_signal(symbol, gran, candles, last_tick)

# CONFIGURAÇÃO DE AMBIENTE
# Lendo variáveis de ambiente (essenciais para o Render)
DERIV_APP_ID = int(os.getenv("DERIV_APP_ID", "114910"))
DERIV_TOKEN = os.getenv("DERIV_TOKEN") # << CHAVE DE AUTENTICAÇÃO
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0") # Leitura, mantendo o 0.0.0.0 como fallback

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Carrega o arquivo index.html (assumindo que ele existe no mesmo diretório)
try:
    with open("index.html", "r", encoding="utf-8") as f:
        INDEX_HTML = f.read()
except FileNotFoundError:
    INDEX_HTML = "<h1>Aplicação rodando!</h1><p>Arquivo index.html não encontrado.</p>"

# Instância do Cliente Deriv
deriv = DerivClient(app_id=DERIV_APP_ID)

# Armazenamento de estado
last_signals = {}
history_ready = set()


# FUNÇÃO CRUCIAL: Tenta conectar automaticamente no STARTUP do servidor
@app.on_event("startup")
async def startup_event():
    """Tenta conectar e autorizar a sessão Deriv usando o token do ambiente."""
    if DERIV_TOKEN:
        print(f"[main] Tentando conectar e autorizar com App ID {DERIV_APP_ID}...")
        # Inicia a conexão em uma tarefa de fundo (não bloqueia o servidor)
        asyncio.create_task(deriv.connect(DERIV_TOKEN))
    else:
        print("[main] AVISO: DERIV_TOKEN não encontrado nas variáveis de ambiente. A conexão deve ser feita manualmente via /set_token.")
    
    print(f"[main] Servidor configurado com HOST: {SERVER_HOST}")


# --- Callbacks do DerivClient ---

def on_history_ready(symbol: str, gran: int):
    history_ready.add((symbol, gran))
    print(f"[main] History ready {symbol}@{gran}")


def on_candle(symbol: str, gran: int, candle_dict: dict):
    key = (symbol, gran)
    try:
        # Garante que a autorização foi bem-sucedida antes de processar
        if deriv.authorized:
            candles = deriv.get_latest_candles(symbol, gran, count=200)
            last_tick = deriv.get_last_tick(symbol)
            sig = strategy.generate_signal(symbol=symbol, gran=gran, candles=candles, last_tick=last_tick)
            if sig:
                sig["generated_at"] = int(time.time())
                last_signals[key] = sig
                print(f"[main] Sinal gerado para {symbol}@{gran}: {sig.get('action')} {sig.get('probability')}")
    except Exception as e:
        print("[main] Erro em on_candle:", e)


def on_tick(tick: dict):
    pass


# Atribuição das Callbacks
deriv.on_history_ready = on_history_ready
deriv.on_candle = on_candle
deriv.on_tick = on_tick


# --- Rotas da API FastAPI ---

@app.get("/", response_class=HTMLResponse)
async def index():
    return INDEX_HTML


@app.post("/set_token")
async def set_token(req: Request):
    """Permite que um cliente defina o token via API (usado como fallback)."""
    data = await req.json()
    token = data.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Nenhum token enviado")
    
    asyncio.create_task(deriv.connect(token))
    return {"ok": True, "message": "Token recebido, conectando..."}


@app.get("/status")
async def status():
    """Retorna o status atual de conexão e autorização."""
    return {
        "connected": deriv.is_connected,
        "authorized": deriv.authorized,
        "app_id": DERIV_APP_ID
    }


@app.get("/subscribe")
async def subscribe(symbol: Optional[str] = "R_100", tf: Optional[int] = 60):
    """Inicia a subscrição de ticks e candles para um ativo/TF."""
    try:
        if not deriv.authorized:
            raise Exception("Erro: Não autorizado. Conecte-se com um token válido primeiro.")
        
        deriv.ensure_candle_builder(symbol, tf)
        asyncio.create_task(deriv.subscribe_candles_history(symbol, granularity=tf, count=200))
        asyncio.create_task(deriv.subscribe_ticks(symbol))
        return {"ok": True, "message": f"Subscribed to {symbol}@{tf}s"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


@app.get("/signal")
async def get_signal(symbol: str = "R_100", tf: int = 60):
    """Retorna o último sinal gerado para o ativo/TF."""
    key = (symbol, tf)
    if key not in history_ready:
        raise HTTPException(status_code=404, detail="Histórico não carregado para esse símbolo/TF. Tente fazer a subscrição primeiro.")
    sig = last_signals.get(key)
    if not sig:
        return {"ok": True, "action": None, "message": "Nenhum sinal claro gerado recentemente."}
    return {"ok": True, **sig}


@app.post("/ia/query")
async def ia_query(req: Request):
    data = await req.json()
    q = data.get("query", "")
    return {"response": f"Pergunta recebida: {q}"}
