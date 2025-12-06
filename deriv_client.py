# deriv_client.py 

import asyncio
import websockets
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
# 🟢 CRÍTICO: Importa a função do strategy.py para atualizar o estado global dos ticks
from strategy import update_ticks 


class DerivClient:
    
    # Seu APP ID mantido
    APP_ID = "114910" 
    DERIV_WS = f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}"

    def __init__(self, token: str):
        self.token = token
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.authorized = False
        # Informações da conta, inicializadas com valores padrão
        self.account_info: Dict[str, Any] = {"balance": 0.0, "currency": "USD", "account_type": "demo"} 
        self.subscribed_symbols: set = set()

    async def _authorize(self):
        """Tenta autorizar o token na Deriv."""
        await self.ws.send(json.dumps({"authorize": self.token}))
        resp = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
        data = json.loads(resp)
        
        if data.get("error"):
            print("[Deriv] Erro authorize:", data["error"])
            return False

        if data.get("msg_type") == "authorize":
            self.authorized = True
            self.account_info.update(data["authorize"])
            self.account_info['account_type'] = 'real' if data["authorize"].get('is_virtual') == 0 else 'demo'
            print(f"[Deriv] Autorizado — Saldo: {self.account_info.get('balance')} {self.account_info.get('currency')}")
            return True
        return False

    async def get_account_info(self):
        """Busca e atualiza as informações da conta."""
        await self.ws.send(json.dumps({"balance": 1}))
        resp = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
        data = json.loads(resp)
        if data.get("balance"):
            self.account_info['balance'] = data['balance'].get('balance', 0.0)

    async def subscribe_to_ticks(self, symbol: str):
        """Subscreve a um novo símbolo e adiciona-o à lista."""
        if symbol not in self.subscribed_symbols:
            await self.ws.send(json.dumps({"ticks": symbol, "subscribe": 1}))
            self.subscribed_symbols.add(symbol)
            print(f"[Deriv] Subscrito: {symbol}")

    async def listen(self):
        """Loop de escuta das mensagens WebSocket."""
        while self.connected:
            try:
                # Timeout de 20s para permitir o envio de Ping
                data = await asyncio.wait_for(self.ws.recv(), timeout=20.0)
                data = json.loads(data)

                # Processamento de Ticks
                if data.get("msg_type") == "tick":
                    tick = data["tick"]
                    price = float(tick["quote"])
                    update_ticks(price) # 🟢 Atualiza o histórico global para Análise e Bots
                    print(f"[Deriv] ✅ Tick recebido para {tick['symbol']}: {price}") 
                    
                # Processamento de Saldos
                if data.get("msg_type") == "balance":
                     if data.get('balance'):
                        self.account_info['balance'] = data['balance'].get('balance', 0.0)
                        
                # Outras mensagens (autorização, etc.) são ignoradas aqui.

            except websockets.ConnectionClosed:
                print("[Deriv] Conexão fechada. Tentando reconectar...")
                self.connected = False
                break
            except asyncio.TimeoutError:
                # Envia um 'ping' para manter a conexão viva
                await self.ws.send(json.dumps({"ping": 1}))
                continue
            except Exception as e:
                print(f"[ERRO GERAL] no listener: {e}")
                await asyncio.sleep(1) # Pequena pausa em caso de erro

    async def start(self):
        """Loop principal que gere a reconexão."""
        while True:
            if not self.token:
                await asyncio.sleep(1)
                continue
            
            try:
                print("[Deriv] Tentando conectar...")
                async with websockets.connect(self.DERIV_WS) as ws:
                    self.ws = ws
                    self.connected = True
                    print("[Deriv] Conexão WebSocket aberta.")

                    # 1. Autorizar
                    if not await self._authorize():
                        await asyncio.sleep(5)
                        continue

                    await self.get_account_info()

                    # 2. Resubscrever aos símbolos ativos
                    for s in list(self.subscribed_symbols):
                        try:
                            await self.subscribe_to_ticks(s)
                        except:
                            pass
                            
                    # 3. Iniciar o leitor de mensagens
                    await self.listen()

            except Exception as e:
                print(f"[Deriv] Erro no loop principal: {e}")

            self.connected = False
            self.authorized = False
            await asyncio.sleep(5) # Espera antes de tentar reconectar

    async def stop(self):
        """Fecha a conexão."""
        try:
            self.connected = False
            self.authorized = False
            if self.ws:
                await self.ws.close()
        except:
            pass
        print("[Deriv] Cliente parado.")


    # 🟢 MÉTODO CRÍTICO DE COMPRA REAL 🟢
    async def buy(self, symbol: str, duration: int, amount: float, action: str):
        """
        Executa a compra de um contrato na Deriv (Proposta + Compra).
        duration é em Ticks. action é 'CALL' ou 'PUT'.
        """
        if not self.ws or not self.authorized:
            print("[Deriv Buy] Não é possível comprar: Desconectado/Não autorizado.")
            return None

        contract_type = action.upper()
        currency = self.account_info.get("currency", "USD")
        
        # 1. Obter Proposta (necessário para ter o ID da proposta)
        proposal_request = {
            "proposal": 1,
            "amount": amount,
            "basis": "stake",
            "contract_type": contract_type,
            "currency": currency,
            "duration": duration,
            "duration_unit": "t", # Ticks
            "symbol": symbol
        }
        
        try:
            await self.ws.send(json.dumps(proposal_request))
            resp = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
            data = json.loads(resp)
        except Exception as e:
            print(f"[Deriv Buy] Erro de comunicação na Proposta: {e}")
            return None
        
        if data.get('error') or data.get('msg_type') != 'proposal':
            msg = data.get('error', {}).get('message', 'Erro desconhecido na proposta')
            print(f"[Deriv Buy] Erro na Proposta: {msg}")
            return None
        
        proposal_id = data['proposal']['id']
        price = data['proposal']['ask_price'] # Preço de compra

        # 2. Executar Compra
        buy_request = {
            "buy": proposal_id,
            "price": price,
        }

        try:
            await self.ws.send(json.dumps(buy_request))
            # Espera a confirmação da compra
            resp_buy = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
            buy_data = json.loads(resp_buy)
        except Exception as e:
            print(f"[Deriv Buy] Erro de comunicação na Compra: {e}")
            return None

        if buy_data.get('error'):
            msg = buy_data.get('error', {}).get('message', 'Erro desconhecido na compra')
            print(f"[Deriv Buy] Erro na Compra: {msg}")
            return None
        
        contract = buy_data.get('buy')
        if contract:
            print(f"[Deriv] 💰 Compra Executada! ID: {contract['contract_id']}")
            return contract

        return None
