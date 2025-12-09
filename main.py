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

# CONFIG
DERIV_APP_ID = int(os.getenv("DERIV_APP_ID", "114910"))
SERVER_HOST = os.getenv("SERVER_HOST", "")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load index.html
with open("index.html", "r", encoding="utf-8") as f:
    INDEX_HTML = f.read()

# single client
deriv = DerivClient(app_id=DERIV_APP_ID)

# last signals store
last_signals = {}
history_ready = set()


# callbacks from deriv_client
def on_history_ready(symbol: str, gran: int):
    history_ready.add((symbol, gran))
    print(f"[main] history ready {symbol} {gran}")


def on_candle(symbol: str, gran: int, candle_dict: dict):
    key = (symbol, gran)
    try:
        candles = deriv.get_latest_candles(symbol, gran, count=200)
        last_tick = deriv.get_last_tick(symbol)
        sig = strategy.generate_signal(symbol=symbol, gran=gran, candles=candles, last_tick=last_tick)
        if sig:
            sig["generated_at"] = int(time.time())
            last_signals[key] = sig
            print(f"[main] signal generated for {symbol}@{gran}: {sig.get('action')} {sig.get('probability')}")
    except Exception as e:
        print("[main] error in on_candle:", e)


def on_tick(tick: dict):
    # optional: could call micro confirmation strategy, but leave minimal
    pass


deriv.on_history_ready = on_history_ready
deriv.on_candle = on_candle
deriv.on_tick = on_tick


# Routes
@app.get("/", response_class=HTMLResponse)
async def index():
    return INDEX_HTML


@app.post("/set_token")
async def set_token(req: Request):
    data = await req.json()
    token = data.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Nenhum token enviado")
    # connect in background
    asyncio.create_task(deriv.connect(token))
    return {"ok": True, "message": "Token recebido, conectando..."}


@app.get("/status")
async def status():
    return {
        "connected": deriv.is_connected,
        "authorized": deriv.authorized,
        "app_id": DERIV_APP_ID
    }


@app.get("/subscribe")
async def subscribe(symbol: Optional[str] = "R_100", tf: Optional[int] = 60):
    try:
        deriv.ensure_candle_builder(symbol, tf)
        asyncio.create_task(deriv.subscribe_candles_history(symbol, granularity=tf, count=200))
        asyncio.create_task(deriv.subscribe_ticks(symbol))
        return {"ok": True, "message": f"Subscribed to {symbol}@{tf}s"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


@app.get("/signal")
async def get_signal(symbol: str = "R_100", tf: int = 60):
    key = (symbol, tf)
    if key not in history_ready:
        raise HTTPException(status_code=404, detail="Histórico não carregado para esse símbolo/TF")
    sig = last_signals.get(key)
    if not sig:
        return {"ok": True, "action": None}
    return {"ok": True, **sig}


@app.post("/ia/query")
async def ia_query(req: Request):
    data = await req.json()
    q = data.get("query", "")
    # placeholder - integrate your AI later
    return {"response": f"Pergunta recebida: {q}"}
