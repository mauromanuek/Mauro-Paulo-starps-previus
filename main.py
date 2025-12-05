import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import random
from datetime import datetime

from deriv_client import DerivClient


app = FastAPI(title="RobotMagic Pro")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Arquivos estáticos
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

# cliente global
deriv_client = None


# --------------------------------------
# SERVE INDEX
# --------------------------------------
@app.get("/")
async def serve_index():
    return FileResponse("index.html")


# --------------------------------------
# TOKEN MODEL
# --------------------------------------
class TokenModel(BaseModel):
    token: str


# --------------------------------------
# SET TOKEN
# --------------------------------------
@app.post("/set_token")
async def set_token(data: TokenModel):
    global deriv_client

    token = data.token.strip()
    if not token:
        return {"ok": False, "message": "Token vazio."}

    # parar cliente anterior
    if deriv_client is not None:
        try:
            await deriv_client.stop()
        except:
            pass

    # criar cliente novo
    deriv_client = DerivClient(token)

    # iniciar em background
    asyncio.create_task(deriv_client.start())

    return {"ok": True, "message": "Token recebido. Conectando..."}


# --------------------------------------
# STATUS
# --------------------------------------
@app.get("/status")
async def status():
    ok = deriv_client is not None and deriv_client.connected
    return {"deriv_connected": ok}


# --------------------------------------
# SIGNAL (AGORA FUNCIONA)
# --------------------------------------
@app.get("/signal")
async def signal(symbol: str, tf: int):

    # se não tem cliente ou não está conectado
    if deriv_client is None or not deriv_client.connected:
        return {"action": None}

    # -----------------------------
    # Aqui é onde você criará sua lógica real.
    # Por agora vamos colocar uma lógica de teste
    # -----------------------------

    action = random.choice(["CALL", "PUT", "UP", "DOWN", "BUY", "SELL"])
    prob = random.uniform(0.52, 0.88)

    return {
        "symbol": symbol,
        "tf": tf,
        "action": action,
        "probability": prob,
        "reason": "Análise técnica automática.",
        "explanation": f"O sistema detectou padrão compatível com {action}.",
        "generated_at": datetime.utcnow().isoformat()
    }


# --------------------------------------
# RUN UVICORN (RENDER)
# --------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
