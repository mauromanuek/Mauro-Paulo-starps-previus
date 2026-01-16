import os
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import requests
import json

app = Flask(__name__)
CORS(app)

# CONFIGURAÇÕES
LINK_DO_BOT = "https://mauromanuek.github.io/Mauro-Paulo-starps-previus/"
# Chave de ambiente configurada no Render
GROQ_API_KEY = os.environ.get("GROQ_API_KEY") 

@app.route('/')
def index():
    return redirect(LINK_DO_BOT)

@app.route('/analisar', methods=['POST'])
def analisar():
    if not GROQ_API_KEY:
        return jsonify({"erro": "Chave GROQ não configurada no Render"}), 500

    dados_mercado = request.json
    
    # Payload otimizado para Scalping e Oportunismo (Problema 3 e 5)
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system", 
                "content": (
                    "Você é um Especialista em Scalping nos Índices Sintéticos da Deriv. "
                    "Sua missão é ser OPORTUNISTA. Analise Price Action e Indicadores para identificar "
                    "micro-tendências e reversões rápidas. Mesmo que a tendência principal seja estável, "
                    "busque entradas de curto prazo. "
                    "Responda EXCLUSIVAMENTE em formato JSON puro: "
                    "{\"direcao\":\"CALL\"|\"PUT\"|\"NEUTRO\", \"confianca\": 0-100, \"motivo\": \"curto\"}"
                )
            },
            {
                "role": "user", 
                "content": f"Dados Técnicos Atuais: {json.dumps(dados_mercado)}"
            }
        ],
        "temperature": 0.4, # Aumentado para permitir identificação de padrões de risco/recompensa
        "max_tokens": 150
    }
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}", 
        "Content-Type": "application/json"
    }

    try:
        # Chamada para API Groq
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=20)
        
        if response.status_code != 200:
            return jsonify({"erro": f"Erro na API Groq: {response.status_code}", "detalhes": response.text}), response.status_code

        res_data = response.json()
        
        if 'choices' in res_data and len(res_data['choices']) > 0:
            content = res_data['choices'][0]['message']['content'].strip()
            
            # Limpeza robusta de Markdown e caracteres extras (Problema 3)
            if "```" in content:
                content = content.split("```")
                content = content[1] if len(content) > 1 else content[0]
                content = content.replace("json", "").strip()
            
            try:
                # Validamos e limpamos o JSON antes de retornar ao frontend
                json_valido = json.loads(content)
                # Forçamos a estrutura correta para evitar erros no parse do JS
                return jsonify({
                    "choices": [{
                        "message": {
                            "content": json.dumps(json_valido)
                        }
                    }]
                })
            except json.JSONDecodeError:
                # Fallback: tenta encontrar JSON dentro de strings sujas
                return jsonify({"erro": "Erro de formatação na IA", "raw": content}), 500
        
        return jsonify({"erro": "Resposta da IA vazia"}), 500

    except requests.exceptions.Timeout:
        return jsonify({"erro": "Timeout na comunicação com Groq"}), 504
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
