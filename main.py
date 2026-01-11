import asyncio
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import uvicorn

from strategy import generate_signal, get_macro_analysis
from deriv_client import DerivClient

app = FastAPI()
client: Optional[DerivClient] = None
# Estado Global do Bot
bot_active = False

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class TokenRequest(BaseModel):
    token: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/login")
async def login(data: TokenRequest):
    global client
    try:
        client = DerivClient(token=data.token)
        asyncio.create_task(client.start())
        await asyncio.sleep(4) 
        if client.authorized:
            return {"status": "success"}
        return {"status": "error", "message": "Token inválido ou erro de conexão."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/account_info")
async def account_info():
    if client and client.authorized:
        return client.account_info
    return {"balance": 0.0, "account_type": "demo"}

@app.get("/get_analysis")
async def get_analysis():
    sinal = generate_signal()
    # Adicionamos o estado atual do bot na resposta da análise
    return {
        "analysis": sinal if sinal else {"status": "waiting"},
        "bot_active": bot_active
    }

@app.get("/macro_stats")
async def macro_stats():
    return get_macro_analysis()

@app.post("/toggle_bot")
async def toggle_bot(active: bool):
    global bot_active
    bot_active = active
    return {"status": "success", "bot_active": bot_active}

@app.post("/emergency_stop")
async def emergency_stop():
    global bot_active
    bot_active = False
    return {"status": "stopped"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
