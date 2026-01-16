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
    
    # Payload otimizado para Scalping Agressivo (Resolve Problemas 2, 4 e 5)
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system", 
                "content": (
                    "Você é um Engenheiro de Trading Quantitativo especialista em Scalping na Deriv. "
                    "Sua estratégia é baseada em Momentum e Rejeição de Preço (Price Action). "
                    "DIRETRIZ: Seja OPORTUNISTA. Procure por sinais de entrada rápida mesmo em tendências curtas. "
                    "Se o RSI estiver em zonas de exaustão ou houver padrões de vela (como Martelo), priorize a entrada. "
                    "REGRAS DE RESPOSTA: "
                    "1. Retorne APENAS JSON puro. "
                    "2. Campos: 'direcao' (CALL, PUT ou NEUTRO), 'confianca' (0-100), 'motivo' (máx 10 palavras). "
                    "3. Não use blocos de código ou explicações fora do JSON."
                )
            },
            {
                "role": "user", 
                "content": f"Analise estes dados OHLC e Indicadores para Scalp M1: {json.dumps(dados_mercado)}"
            }
        ],
        "temperature": 0.6, # Aumentado para reduzir neutralidade excessiva
        "max_tokens": 100,
        "response_format": {"type": "json_object"} # Força a API a retornar JSON válido
    }
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}", 
        "Content-Type": "application/json"
    }

    try:
        # Chamada para API Groq com tratamento de tempo de resposta
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions", 
            json=payload, 
            headers=headers, 
            timeout=25
        )
        
        if response.status_code != 200:
            return jsonify({
                "erro": f"Erro na API Groq: {response.status_code}", 
                "detalhes": response.text
            }), response.status_code

        res_data = response.json()
        
        if 'choices' in res_data and len(res_data['choices']) > 0:
            content = res_data['choices'][0]['message']['content'].strip()
            
            try:
                # Parse do conteúdo retornado pela IA
                veredito = json.loads(content)
                
                # Normalização de Segurança (Garante que o Frontend receba o que espera)
                veredito['direcao'] = str(veredito.get('direcao', 'NEUTRO')).upper()
                veredito['confianca'] = int(veredito.get('confianca', 0))
                
                # Encapsulamento no formato esperado pelo analiseGeral.js
                return jsonify({
                    "choices": [{
                        "message": {
                            "content": json.dumps(veredito)
                        }
                    }]
                })
            except (json.JSONDecodeError, ValueError) as e:
                # Em caso de erro de formato, enviamos um log para o frontend tratar
                return jsonify({"erro": "IA retornou formato inválido", "raw": content}), 500
        
        return jsonify({"erro": "Resposta da IA vazia ou malformada"}), 500

    except requests.exceptions.Timeout:
        return jsonify({"erro": "A API da Groq demorou muito para responder"}), 504
    except Exception as e:
        return jsonify({"erro": f"Erro interno no servidor: {str(e)}"}), 500

if __name__ == '__main__':
    # O Render fornece a porta automaticamente pela variável de ambiente PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
