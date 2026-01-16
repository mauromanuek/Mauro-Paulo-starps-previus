import os
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import requests
import json

app = Flask(__name__)
CORS(app)

# CONFIGURAÇÕES
LINK_DO_BOT = "https://mauromanuek.github.io/Mauro-Paulo-starps-previus/"
# IMPORTANTE: No Render, agora você criará a chave GROQ_API_KEY
GROQ_API_KEY = os.environ.get("GROQ_API_KEY") 

@app.route('/')
def index():
    return redirect(LINK_DO_BOT)

@app.route('/analisar', methods=['POST'])
def analisar():
    if not GROQ_API_KEY:
        return jsonify({"erro": "Chave GROQ não configurada no Render"}), 500

    dados_mercado = request.json
    
    # Payload configurado para o modelo Llama 3.3 do Groq
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system", 
                "content": "Você é um validador de tendência para a Deriv. Analise os dados e responda estritamente em formato JSON puro, sem blocos de código markdown e sem texto adicional. Estrutura: {\"direcao\":\"CALL\"|\"PUT\"|\"NEUTRO\", \"confianca\": 0-100, \"motivo\": \"curto\"}"
            },
            {
                "role": "user", 
                "content": f"Dados do Mercado: {json.dumps(dados_mercado)}"
            }
        ],
        "temperature": 0.1, # Temperatura baixa para maior precisão matemática
        "max_tokens": 150
    }
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}", 
        "Content-Type": "application/json"
    }

    try:
        # URL da API do Groq
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=20)
        
        if response.status_code != 200:
            return jsonify({"erro": f"Erro na API Groq: {response.status_code}", "detalhes": response.text}), response.status_code

        res_data = response.json()
        
        if 'choices' in res_data and len(res_data['choices']) > 0:
            content = res_data['choices'][0]['message']['content'].strip()
            
            # Limpeza rigorosa de Markdown
            if "```" in content:
                content = content.split("```")[1].replace("json", "").strip()
            
            try:
                # Validamos se é um JSON antes de devolver ao Bot
                json_valido = json.loads(content)
                return jsonify({
                    "choices": [{
                        "message": {
                            "content": json.dumps(json_valido)
                        }
                    }]
                })
            except json.JSONDecodeError:
                return jsonify({"erro": "Formato de resposta inválido", "raw": content}), 500
        
        return jsonify({"erro": "Resposta da IA vazia"}), 500

    except requests.exceptions.Timeout:
        return jsonify({"erro": "Timeout na comunicação com Groq"}), 504
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    # O Render usa a porta 10000 por padrão
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
