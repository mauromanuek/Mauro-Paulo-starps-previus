# main.py
# Servidor base do bot — Versão inicial (estável para Render)

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI()

# Modelo para receber dados do HTML
class MarketData(BaseModel):
    ticks: list = []
    candles: list = []

# Rota inicial para teste
@app.get("/")
def home():
    return {"status": "Servidor ativo! 🚀"}

# Rota que recebe dados do navegador
@app.post("/analyze")
def analyze(data: MarketData):
    # Ainda não estamos rodando IA — isso vem depois
    # Aqui só devolvemos uma resposta para testar a conexão
    return {
        "message": "Dados recebidos com sucesso!",
        "n_ticks": len(data.ticks),
        "n_candles": len(data.candles)
    }

# Render usa esta função como ponto de entrada
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
