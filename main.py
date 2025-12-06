import os
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from deriv_client import DerivClient
from bots_manager import BotsManager
from strategy import Strategy

# ---------------------------------------------------------
# CONFIGURAÇÃO DO APP_ID
# ---------------------------------------------------------
DERIV_APP_ID = int(os.getenv("DERIV_APP_ID", "114910"))

# Cliente global
deriv_client = DerivClient(app_id=DERIV_APP_ID)

# Bots manager
bots = BotsManager(deriv_client)

app = FastAPI()

# Servir arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------
# RENDERIZAR INTERFACE
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------
# DEFINIR TOKEN
# ---------------------------------------------------------
@app.post("/set_token")
async def set_token(request: Request):
    data = await request.json()
    token = data.get("token")

    if not token:
        return JSONResponse({"error": "Nenhum token enviado."}, status_code=400)

    deriv_client.token = token

    asyncio.create_task(deriv_client.connect())

    return {"status": "Token recebido", "app_id": DERIV_APP_ID}


# ---------------------------------------------------------
# STATUS DO BOT
# ---------------------------------------------------------
@app.get("/status")
async def status():
    return {
        "connected": deriv_client.connected,
        "balance": deriv_client.balance,
        "account_type": deriv_client.account_type,
        "app_id": DERIV_APP_ID
    }
