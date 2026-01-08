import asyncio
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import uvicorn

from strategy import generate_signal 
from deriv_client import DerivClient

app = FastAPI()
client: Optional[DerivClient] = None

# Montar pasta static e templates
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
        # Tenta conectar com o token fornecido
        client = DerivClient(token=data.token)
        asyncio.create_task(client.start())
        
        # Aguarda 3 segundos para verificar se a Deriv autorizou
        await asyncio.sleep(3)
        
        if client.authorized:
            return {"status": "success"}
        else:
            return {"status": "error", "message": "Token inválido ou falha na conexão com a Deriv."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/account_info")
async def account_info():
    if client and client.authorized:
        return client.account_info
    return {"balance": 0.0, "account_type": "None"}

@app.get("/get_analysis")
async def get_analysis():
    sinal = generate_signal()
    if sinal:
        return {"status": "active", **sinal}
    return {"status": "waiting"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
