import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from deriv_client import DerivClient


app = FastAPI(title="Bot Trader Deriv")

# Permitir comunicação do frontend com o backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir arquivos HTML diretamente da raiz
app.mount("/", StaticFiles(directory=".", html=True), name="static")

# Cliente global (inicia vazio)
deriv_client = None


# Modelo para POST /set_token
class TokenModel(BaseModel):
    token: str


@app.post("/set_token")
async def set_token(data: TokenModel):
    """
    Recebe o token da Deriv enviado pelo frontend,
    reinicia o cliente e conecta novamente.
    """
    global deriv_client

    token = data.token.strip()

    if not token:
        return {"ok": False, "message": "Token vazio!"}

    # Se já existe cliente, parar antes de reiniciar
    if deriv_client is not None:
        try:
            await deriv_client.stop()
        except:
            pass

    # Criar novo cliente com o token enviado
    deriv_client = DerivClient(token)

    # Iniciar conexão em background
    asyncio.create_task(deriv_client.start())

    return {"ok": True, "message": "Conectado à Deriv!"}


@app.get("/status")
async def status():
    """
    Retorna o status atual da conexão com a Deriv.
    """
    online = deriv_client is not None and deriv_client.connected
    return {"deriv_connected": online}


# 🔥 Servidor uvicorn para funcionar no Render
if __name__ == "__main__":
    import uvicorn
    import os

    # Render informa a porta via variável de ambiente PORT
    port = int(os.environ.get("PORT", 10000))

    uvicorn.run("main:app", host="0.0.0.0", port=port)
