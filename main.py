from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import asyncio
import json
from deriv_client import client
from strategy import calculate_signal
from config import PORT, DEFAULT_SYMBOL

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Mock de histórico para o exemplo (Em prod, isso viria do stream real)
tick_history = []

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/login")
async def login(token: str = Form(...)):
    await client.connect()
    auth = await client.authorize(token)
    return auth

@app.get("/get_analysis")
async def get_analysis():
    # Simulação de captura de ticks para fins de exemplo
    # Em produção, um loop 'async for' capturaria os ticks do WebSocket
    signal = calculate_signal(tick_history[-60:]) 
    return signal

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
