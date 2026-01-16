import os
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import requests
import json

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
    
    # Payload otimizado para garantir resposta parseável
    payload = {
        "model": "grok-beta",
        "messages": [
            {
                "role": "system", 
                "content": "Você é um validador de tendência para a Deriv. Responda estritamente em formato JSON puro, sem explicações e sem blocos de código Markdown. Estrutura: {'direcao':'CALL'|'PUT'|'NEUTRO', 'confianca': 0-100, 'motivo': 'curto'}"
            },
            {
                "role": "user", 
                "content": f"Contexto: {dados_mercado.get('contexto')}. Indicadores: {dados_mercado.get('indicadores')}"
            }
        ],
        "temperature": 0.2
    }
    
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}", 
        "Content-Type": "application/json"
    }

    try:
        response = requests.post("https://api.x.ai/v1/chat/completions", json=payload, headers=headers, timeout=25)
        
        if response.status_code != 200:
            return jsonify({"erro": f"Erro na API Grok: {response.status_code}", "detalhes": response.text}), response.status_code

        res_data = response.json()
        
        # Validação da estrutura de resposta da xAI
        if 'choices' in res_data and len(res_data['choices']) > 0:
            content = res_data['choices'][0]['message']['content'].strip()
            
            # Limpeza de possíveis blocos Markdown que a IA possa gerar por vício
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            # Tenta validar se o conteúdo final é um JSON válido
            try:
                json_valido = json.loads(content)
                # Reconstrói a resposta para garantir consistência para o Frontend
                res_data['choices'][0]['message']['content'] = json.dumps(json_valido)
                return jsonify(res_data)
            except json.JSONDecodeError:
                return jsonify({"erro": "IA retornou formato inválido", "raw": content}), 500
        
        return jsonify({"erro": "Resposta da IA incompleta"}), 500

    except requests.exceptions.Timeout:
        return jsonify({"erro": "Timeout na comunicação com Grok"}), 504
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
