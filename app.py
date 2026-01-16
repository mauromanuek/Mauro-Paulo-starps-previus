from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app) # Resolve o bloqueio do navegador

# A CHAVE FICA AQUI, LONGE DO HTML
GROK_API_KEY = "xai-VMufbThWmMU35plvCkgTu1cFHY3JTawcWha4PKKJpXlRFSJmt4QUB63gVWwiXxwwAVBKa922p2S4Lwfg"

@app.route('/analisar', methods=['POST'])
def analisar():
    dados_mercado = request.json
    
    # Payload para o Grok focado em Filtro de Qualidade
    payload = {
        "model": "grok-beta",
        "messages": [
            {"role": "system", "content": "Você é um validador de tendência. Responda APENAS JSON: {'direcao':'CALL'|'PUT'|'NEUTRO', 'confianca': 0-100, 'motivo': 'curto'}"},
            {"role": "user", "content": f"Analise este contexto: {dados_mercado['contexto']}. Indicadores: {dados_mercado['indicadores']}"}
        ],
        "temperature": 0.3
    }

    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post("https://api.x.ai/v1/chat/completions", json=payload, headers=headers)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    # Ajuste para rodar no Render (porta 10000 e host 0.0.0.0)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
