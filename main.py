import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os

from deriv_client import DerivClient

app = FastAPI(title="Bot Trader Deriv")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Cliente global
deriv_client = None


# -----------------------------
# Servir a interface corretamente
# -----------------------------
@app.get("/")
async def serve_index():
    return FileResponse("index.html")


# Modelo do token
class TokenModel(BaseModel):
    token: str


# -----------------------------
# Rota para receber o token
# -----------------------------
@app.post("/set_token")
async def set_token(data: TokenModel):
    global deriv_client

    token = data.token.strip()
    if not token:
        return {"ok": False, "message": "Token vazio!"}

    # Parar cliente antigo
    if deriv_client is not None:
        try:
            await deriv_client.stop()
        except:
            pass

    # Criar novo cliente
    deriv_client = DerivClient(token)

    # Iniciar conexão
    asyncio.create_task(deriv_client.start())

    return {"ok": True, "message": "Token recebido! Tentando conectar..."}


# -----------------------------
# Status da conexão
# -----------------------------
@app.get("/status")
async def status():
    online = deriv_client is not None and deriv_client.connected
    return {"deriv_connected": online}


# -----------------------------
# Iniciar servidor no Render
# -----------------------------
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
