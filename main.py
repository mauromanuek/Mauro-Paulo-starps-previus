# main.py
# RobotMagic Pro — Servidor FastAPI (Backend Principal)

import os
import asyncio
import datetime
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from deriv_client import DerivClient
from bots_manager import BotsManager

app = FastAPI(title="RobotMagic Pro API")

# Estado global
STATE = {
    "last_signal": None,
    "history": [],
    "symbols": ["R_100", "R_50", "FRXEURUSD"],
    "deriv_connected": False,
}

# Instanciar clientes
DERIV_TOKEN = os.environ.get("DERIV_API_TOKEN")  # opcional
deriv = DerivClient(token=DERIV_TOKEN, on_tick_callback=None)
bots = BotsManager()

# CALLBACK: sempre que deriv_client gerar um sinal
def on_new_signal(sig):
    STATE["last_signal"] = sig
    STATE["history"].append(sig)
    if len(STATE["history"]) > 500:
        STATE["history"].pop(0)

deriv.on_signal = on_new_signal


# MODELOS

class SignalRequest(BaseModel):
    symbol: Optional[str] = "R_100"
    tf: Optional[int] = 60

class CreateBotSpec(BaseModel):
    name: str
    mode: str = "sandbox"         # sandbox ou real
    stake: float = 1.0
    max_trades_per_hour: int = 10


# STARTUP — conectar ao WebSocket da Deriv (se houver token)
@app.on_event("startup")
async def startup_event():
    if DERIV_TOKEN:
        asyncio.create_task(deriv.run())
        STATE["deriv_connected"] = True
    else:
        STATE["deriv_connected"] = False


# -------------------------------
# ENDPOINTS PRINCIPAIS
# -------------------------------

@app.get("/")
async def root():
    return {
        "status": "Servidor ativo! 🚀",
        "deriv_connected": STATE["deriv_connected"]
    }

@app.get("/health")
async def health():
    return {"ok": True, "utc_time": datetime.datetime.utcnow().isoformat()}


# -------------------------------
# ENDPOINT DE SINAIS
# -------------------------------

@app.get("/signal")
async def get_signal(symbol: Optional[str] = "R_100", tf: Optional[int] = 60):

    # Se deriv gerou sinal recente
    s = STATE.get("last_signal")
    if s and s.get("symbol") == symbol:
        return s

    # Caso contrário, gerar um sinal provisório (DEMO)
    now = datetime.datetime.utcnow()
    sec = now.second

    if sec % 45 < 8:
        action = "CALL"
        prob = 0.82
        reason = "Rompimento + Volume crescente"
    elif sec % 45 < 16:
        action = "PUT"
        prob = 0.74
        reason = "Reversão com candle forte"
    else:
        return {"action": None, "probability": 0.0, "message": "Sem sinal no momento"}

    entry_time = (now + datetime.timedelta(seconds=10)).isoformat() + "Z"

    sig = {
        "id": str(uuid.uuid4()),
        "symbol": symbol,
        "tf": tf,
        "action": action,
        "probability": prob,
        "reason": reason,
        "explanation": "Explicação técnica: tendência + padrão + volume + confirmação.",
        "entry": entry_time,
        "generated_at": now.isoformat() + "Z"
    }

    STATE["last_signal"] = sig
    STATE["history"].append(sig)
    return sig


# -------------------------------
# ENDPOINT DE ANÁLISE TÉCNICA
# -------------------------------

@app.get("/analysis")
async def analysis(symbol: Optional[str] = "R_100", tf: Optional[int] = 60):
    return {
        "symbol": symbol,
        "tf": tf,
        "supports": [],
        "resistances": [],
        "indicators": {"rsi": 52, "macd": "flat", "volume": "moderado"},
        "notes": "Análise provisória — IA ainda será integrada."
    }


# -------------------------------
# BOTS — CRIAR / ATIVAR / DESATIVAR
# -------------------------------

@app.post("/bots/create")
def create_bot(spec: CreateBotSpec):
    bot_id = bots.create_bot(spec.dict())
    return {"bot_id": bot_id, "bot": bots.get_bot(bot_id)}

@app.post("/bots/{bot_id}/activate")
def activate_bot(bot_id: str, simulate: Optional[bool] = True):

    bot = bots.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot não encontrado")

    # Modo real exige token no servidor
    if (not simulate) and (not DERIV_TOKEN):
        raise HTTPException(status_code=400,
                            detail="Não é possível ativar em modo 'real' sem DERIV_API_TOKEN no servidor.")

    bots.activate_bot(bot_id, simulate=simulate)
    return {"ok": True, "bot": bots.get_bot(bot_id)}

@app.post("/bots/{bot_id}/deactivate")
def deactivate_bot(bot_id: str):
    bot = bots.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot não encontrado")

    bots.deactivate_bot(bot_id)
    return {"ok": True}

@app.get("/bots")
def list_bots():
    return bots.list_bots()


# -------------------------------
# DEBUG — empurrar sinal MANUAL
# -------------------------------

class PushSignal(BaseModel):
    symbol: str
    action: str
    probability: float
    reason: Optional[str] = None

@app.post("/debug/push_signal")
def push_signal(p: PushSignal):

    now = datetime.datetime.utcnow()
    sig = {
        "id": str(uuid.uuid4()),
        "symbol": p.symbol,
        "tf": 60,
        "action": p.action,
        "probability": p.probability,
        "reason": p.reason or "Debug manual",
        "explanation": "Sinal inserido manualmente",
        "entry": (now + datetime.timedelta(seconds=10)).isoformat() + "Z",
        "generated_at": now.isoformat() + "Z"
    }

    STATE["last_signal"] = sig
    STATE["history"].append(sig)
    return {"ok": True, "signal": sig}


# -------------------------------
# EXECUÇÃO LOCAL (Render ignora)
# -------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=10000, log_level="info")
