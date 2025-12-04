import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from deriv_client import DerivClient

app = FastAPI(title="Bot Trader Deriv")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir interface
app.mount("/", StaticFiles(directory=".", html=True), name="static")

deriv_client = None  # será inicializado após receber token


class TokenModel(BaseModel):
    token: str


@app.post("/set_token")
async def set_token(data: TokenModel):
    global deriv_client

    token = data.token.strip()

    if not token:
        return {"ok": False, "message": "Token vazio!"}

    # Se já existir cliente, parar e reiniciar
    if deriv_client is not None:
        try:
            await deriv_client.stop()
        except:
            pass

    # Criar novo cliente com o token recebido
    deriv_client = DerivClient(token)

    # Iniciar conexão em background
    asyncio.create_task(deriv_client.start())

    return {"ok": True, "message": "Conectado à Deriv com sucesso!"}


@app.get("/status")
async def status():
    return {"status": "Servidor ativo!"}
