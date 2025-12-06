# deriv_client.py 

import asyncio
import websockets
import json
from datetime import datetime
# Adicionado calculate_indicators, assumindo que foi definido no seu strategy.py
from strategy import update_ticks, calculate_indicators 
from typing import Dict, Any, Optional

class DerivClient:
    
    # SEU APP ID INSERIDO AQUI
    APP_ID = "114910" 
    URL = f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}"

    def __init__(self, token: str):
        self.token = token
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.authorized = False
        self.account_info = {"balance": 0.0, "account_type": "demo", "currency": "USD"} 
        self.last_price = 0.0
        self.indicators_data = {} # 🟢 NOVO: Armazena os indicadores calculados

    async def start(self):
        """Inicia a conexão completa com a Deriv."""
        try:
            self.ws = await websockets.connect(self.URL)
            print("[Deriv] Conexão WebSocket aberta.")
            self.connected = True
            await self.authorize()

            if self.authorized:
                await self.get_account_info() 
                # Subscrição para o índice de volatilidade R_100
                await self.subscribe_to_ticks("R_100") 
                
                # Inicia o listener em background
                asyncio.create_task(self.listen())
                print("[Deriv] Tarefa de listener iniciada.")

        except Exception as e:
            print(f"[Deriv] Falha ao iniciar cliente: {e}")
            self.connected = False
            self.authorized = False

    async def stop(self):
        """Fecha a conexão e limpa o estado."""
        try:
            # Garante que a flag seja False antes de fechar
            self.connected = False
            self.authorized = False
            if self.ws:
                await self.ws.close()
        except:
            pass
        print("[Deriv] Cliente parado.")
        
    async def get_account_info(self):
        """Busca saldo e informações da conta."""
        request = {"get_settings": 1}
        await self.ws.send(json.dumps(request))

    async def authorize(self):
        """Envia o token para autorização."""
        request = {"authorize": self.token}
        await self.ws.send(json.dumps(request))
        
        # Aguarda a resposta de autorização
        try:
            response_str = await asyncio.wait_for(self.ws.recv(), timeout=5)
            response = json.loads(response_str)
            if response.get("msg_type") == "authorize" and "authorize" in response:
                self.authorized = True
                self.account_info["account_name"] = response["authorize"].get("fullname", "Conta Deriv")
                self.account_info["currency"] = response["authorize"].get("currency", "USD")
                self.account_info["balance"] = response["authorize"].get("balance", 0.0)
                self.account_info["account_type"] = "REAL" if "CR" in response["authorize"]["loginid"] else "DEMO"
            
        except (asyncio.TimeoutError, websockets.ConnectionClosed):
            print("[Deriv] Tempo limite ou conexão fechada durante a autorização.")
        except Exception as e:
            print(f"[Deriv] Erro ao processar autorização: {e}")

    async def subscribe_to_ticks(self, symbol: str):
        """Subscreve para receber ticks em tempo real."""
        request = {"ticks": symbol, "subscribe": 1}
        await self.ws.send(json.dumps(request))

    async def listen(self):
        """Loop principal para receber e processar mensagens do WebSocket."""
        while self.connected:
            try:
                message = await self.ws.recv()
                data = json.loads(message)

                if data.get("msg_type") == "tick":
                    tick = data["tick"]
                    price = float(tick["quote"])
                    update_ticks(price) 
                    self.last_price = price
                    
                    # 🟢 CRÍTICO: Cálculo de Indicadores
                    self.indicators_data = calculate_indicators()
                    
                    print(f"[Deriv] ✅ Tick recebido: {price}")
                    
                # Processamento de Saldos
                if data.get("msg_type") == "balance" and data.get('balance'):
                    self.account_info['balance'] = data['balance'].get('balance', 0.0)
                
                if data.get("msg_type") == "error":
                    print(f"[Deriv] ERRO API: {data.get('error', {}).get('message')}")
                    
            except websockets.ConnectionClosed as e:
                print(f"[Deriv] Conexão fechada. Motivo: {e}. Desligando cliente.")
                self.connected = False
                break
            except asyncio.TimeoutError:
                await self.ws.send(json.dumps({"ping": 1}))
                print("[Deriv] Ping enviado para manter conexão...") 
                continue
            except Exception as e:
                print(f"[ERRO GERAL] no listener: {e}")
                continue

    # --- 🎯 MÉTODO CRÍTICO PARA INTERAÇÃO (BUY) 🎯 ---
    async def buy(self, symbol: str, duration: int, amount: float, contract_type: str):
        """
        Envia a ordem de compra ('CALL') ou venda ('PUT') para a API da Deriv.
        """
        if not self.authorized or not self.ws:
            print("[Deriv] Erro: Não autorizado ou desconectado para enviar ordem.")
            return None
            
        # Mapeamento do tipo de contrato para o formato da API Deriv
        if contract_type == "BUY":
            contract_type = "CALL"
        elif contract_type == "SELL":
            contract_type = "PUT"
        
        buy_request = {
            "buy": 1,
            "price": amount,  # Valor da aposta (stake)
            "parameters": {
                "amount": amount,
                "basis": "stake", 
                "contract_type": contract_type,
                "currency": self.account_info.get("currency", "USD"),
                "duration": duration,
                "duration_unit": "t", # t = ticks.
                "symbol": symbol
            }
        }
        
        try:
            await self.ws.send(json.dumps(buy_request))
            print(f"[Deriv] 💸 Ordem de {contract_type} enviada: {amount} {symbol}")
        except Exception as e:
            print(f"[Deriv] ❌ Erro ao enviar ordem: {e}")
            return None
    
    # 🟢 NOVO MÉTODO: Aceder aos indicadores
    def get_current_indicators(self) -> Dict[str, Any]:
        """Retorna os indicadores calculados e o último preço."""
        return self.indicators_data
