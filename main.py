# main.py
# RobotMagic Pro — Servidor FastAPI (Backend + interface + set_token endpoint)
# Versão: token enviado pela interface (em memória) -> reconexão on-demand

import os
import asyncio
import datetime
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# imports locais
from deriv_client import DerivClient
from bots_manager import BotsManager

# para servir HTML
from fastapi.staticfiles import StaticFiles

# App
app = FastAPI(title="RobotMagic Pro API")

# Servir arquivos estáticos da raiz (index.html etc.)
app.mount("/", StaticFiles(directory=".", html=True), name="static")

# Estado global
STATE = {
    "last_signal": None,
    "history": [],
    "symbols": ["R_100", "R_50", "FRXEURUSD"],
    "deriv_connected": False,
    "deriv_token": None  # token em memória (não persiste em disco)
}

# Instanciar gerenciadores
deriv = DerivClient()  # sem token inicial
bots = BotsManager()

# callback de sinal do deriv_client -> atualiza STATE
def on_new_signal(sig):
    STATE["last_signal"] = sig
    STATE["history"].append(sig)
    if len(STATE["history"]) > 500:
        STATE["history"].pop(0)

deriv.on_signal = on_new_signal


# MODELOS
class TokenModel(BaseModel):
    token: str

class CreateBotSpec(BaseModel):
    name: str
    mode: str = "sandbox"         # sandbox ou real
    stake: float = 1.0
    max_trades_per_hour: int = 10

class PushSignal(BaseModel):
    symbol: str
    action: str
    probability: float
    reason: Optional[str] = None


# STARTUP: nada a fazer (deriv conecta somente quando token enviado)
@app.on_event("startup")
async def startup_event():
    # deriv.run não inicia automaticamente — espera token via /set_token
    STATE["deriv_connected"] = False


# API Root (informativa)
@app.get("/api")
async def api_root():
    return {
        "status": "Servidor ativo! 🚀",
        "deriv_connected": STATE["deriv_connected"],
        "message": "Acesse a interface em /index.html"
    }

@app.get("/health")
async def health():
    return {"ok": True, "utc_time": datetime.datetime.utcnow().isoformat()}


# ENDPOINT para que a interface envie o token e o servidor conecte ao WS da Deriv
@app.post("/set_token")
async def set_token(payload: TokenModel):
    token = payload.token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token vazio")

    # se já havia token/cliente rodando, pare-o de forma segura
    try:
        # se existir conexão ativa, pare
        await deriv.stop_async()
    except Exception:
        # ignore erros de parada
        pass

    # configurar novo cliente com token e callback
    deriv.reset()  # limpa estado interno
    deriv.token = token
    deriv.on_signal = on_new_signal

    # iniciar loop de conexão em background
    asyncio.create_task(deriv.run())

    # atualizar estado
    STATE["deriv_connected"] = True
    STATE["deriv_token"] = True  # apenas marca que token está ativo (não armazenamos o token em STATE em texto)
    return {"ok": True, "message": "Token recebido. Conectando à Deriv..."}


# ENDPOINT para desconectar (opcional)
@app.post("/unset_token")
async def unset_token():
    try:
        await deriv.stop_async()
    except Exception:
        pass
    deriv.reset()
    STATE["deriv_connected"] = False
    STATE["deriv_token"] = None
    return {"ok": True, "message": "Desconectado. Token removido da sessão."}


# SINAL (retorna sinal atual -- deriv real ou demo)
@app.get("/signal")
async def get_signal(symbol: Optional[str] = "R_100", tf: Optional[int] = 60):
    s = STATE.get("last_signal")
    if s and s.get("symbol") == symbol:
        return s

    # fallback demo signal
    now = datetime.datetime.utcnow()
    sec = now.second
    if sec % 45 < 8:
        action = "CALL"
        prob = 0.82
        reason = "Rompimento + Volume crescente (demo)"
    elif sec % 45 < 16:
        action = "PUT"
        prob = 0.74
        reason = "Reversão com candle forte (demo)"
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
        "explanation": "Sinal demo gerado pelo servidor (use token para sinais reais).",
        "entry": entry_time,
        "generated_at": now.isoformat() + "Z"
    }
    STATE["last_signal"] = sig
    STATE["history"].append(sig)
    return sig


# analysis endpoint (placeholder)
@app.get("/analysis")
async def analysis(symbol: Optional[str] = "R_100", tf: Optional[int] = 60):
    return {
        "symbol": symbol,
        "tf": tf,
        "supports": [],
        "resistances": [],
        "indicators": {"rsi": 52, "macd": "flat", "volume": "moderado"},
        "notes": "Análise provisória — IA será integrada."
    }


# BOTS endpoints (reaproveitando BotsManager)
@app.post("/bots/create")
def create_bot(spec: CreateBotSpec):
    bot_id = bots.create_bot(spec.dict())
    return {"bot_id": bot_id, "bot": bots.get_bot(bot_id)}

@app.post("/bots/{bot_id}/activate")
def activate_bot(bot_id: str, simulate: Optional[bool] = True):
    bot = bots.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot não encontrado")
    # se modo real e servidor não conectado -> rejeitar
    if (not simulate) and (not STATE["deriv_connected"]):
        raise HTTPException(status_code=400, detail="Servidor não conectado à Deriv; não é possível ativar modo real.")
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


# Debug endpoint para push de sinal manual (útil para testes)
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


# execução local (uvicorn)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=10000, log_level="info")
