import os
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# CONFIGURAÇÕES
LINK_DO_BOT = "https://mauromanuek.github.io/Mauro-Paulo-starps-previus/"
GROK_API_KEY = os.environ.get("GROK_API_KEY") # BUSCA A CHAVE NO RENDER

@app.route('/')
def index():
    return redirect(LINK_DO_BOT)

@app.route('/analisar', methods=['POST'])
def analisar():
    if not GROK_API_KEY:
        return jsonify({"erro": "Chave não configurada no Render"}), 500

    dados_mercado = request.json
    payload = {
        "model": "grok-beta",
        "messages": [
            {"role": "system", "content": "Você é um validador de tendência. Responda APENAS JSON: {'direcao':'CALL'|'PUT'|'NEUTRO', 'confianca': 0-100, 'motivo': 'curto'}"},
            {"role": "user", "content": f"Analise este contexto: {dados_mercado.get('contexto')}. Indicadores: {dados_mercado.get('indicadores')}"}
        ],
        "temperature": 0.3
    }
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}

    try:
        response = requests.post("https://api.x.ai/v1/chat/completions", json=payload, headers=headers)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
