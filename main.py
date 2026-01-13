import asyncio
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

from strategy import generate_signal 
from deriv_client import DerivClient
from core.executor import TradeExecutor
from bots_manager import BotsManager

app = FastAPI()
client: Optional[DerivClient] = None
manager = BotsManager()
executor: Optional[TradeExecutor] = None

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class TradeRequest(BaseModel):
    action: str
    amount: float
    symbol: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/login")
async def login(data: dict):
    global client, executor
    try:
        client = DerivClient(token=data['token'])
        asyncio.create_task(client.start())
        await asyncio.sleep(4)
        if client.authorized:
            executor = TradeExecutor(client)
            return {"status": "success"}
        return {"status": "error", "message": "Token inválido"}
    except:
        return {"status": "error", "message": "Erro de conexão"}

@app.post("/execute_manual")
async def execute_manual(data: TradeRequest):
    if executor:
        res = await executor.execute_trade(data.action, data.amount, data.symbol)
        return res
    return {"status": "error", "message": "Não conectado"}

@app.get("/get_analysis")
async def get_analysis():
    sinal = generate_signal()
    return sinal if sinal else {"status": "waiting"}

@app.get("/account_info")
async def account_info():
    if client and client.authorized:
        return client.account_info
    return {"balance": 0.0, "account_type": "demo"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
