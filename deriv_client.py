# deriv_client.py 

import asyncio
import websockets
import json
from datetime import datetime
from strategy import update_ticks 
from typing import Dict, Any, Optional

class DerivClient:
    
    # SEU APP ID INSERIDO AQUI
    APP_ID = "114910" 
    WS_URL = f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}"

    def __init__(self, token: str):
        self.token = token
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.authorized = False
        # Valores padrão para evitar erros no main.py
        self.account_info: Dict[str, Any] = {"balance": 0.0, "account_type": "demo", "currency": "USD", "account_name": "N/A"}
        
        # 🟢 CRÍTICO: Eventos para esperar respostas da API
        self.auth_event = asyncio.Event() 
        self.info_event = asyncio.Event() 

    async def start(self):
        """Inicia a conexão completa com a Deriv e espera pelos dados da conta."""
        try:
            self.ws = await websockets.connect(self.WS_URL)
            print("[Deriv] Conexão WebSocket aberta.")
            self.connected = True
            
            # 1. Inicia o listener ANTES de enviar requisições
            asyncio.create_task(self.listen())
            print("[Deriv] Tarefa de listener iniciada.")

            # 2. Autorização (força o código a esperar)
            await self.authorize()
            # 🚨 Espera até 10s pela resposta de autorização
            await asyncio.wait_for(self.auth_event.wait(), timeout=10) 
            
            if not self.authorized:
                raise Exception("Autorização falhou.")

            print("[Deriv] Token autorizado com sucesso. O bot está ONLINE.")
            
            # 3. Informações da Conta (força o código a esperar)
            await self.get_account_info() 
            # 🚨 Espera até 10s pela resposta das informações de conta
            await asyncio.wait_for(self.info_event.wait(), timeout=10) 
            print("[Deriv] DEBUG: Informações da conta processadas.") 
                
            # 4. Subscrição de Ticks
            await self.subscribe_to_ticks("R_100") 
            
        except asyncio.TimeoutError:
            print("[Deriv] ERRO: Timeout ao esperar pela resposta da Deriv. (Dados de Login/Conta não chegaram a tempo).")
            await self.stop()
            self.authorized = False
        except Exception as e:
            print(f"[Deriv] ERRO no start: {e}")
            await self.stop()
            self.authorized = False

    async def authorize(self):
        """Envia a requisição de autorização."""
        req = {"authorize": self.token}
        await self.ws.send(json.dumps(req))

    async def get_account_info(self):
        """Subscreve para obter o saldo e informações da conta."""
        # 1. Obter saldo (e subscrição de atualizações de saldo)
        await self.ws.send(json.dumps({"balance": 1, "subscribe": 1}))
        # 2. Obter informações da conta (tipo de conta, moeda, email)
        await self.ws.send(json.dumps({"get_settings": 1}))
    
    async def subscribe_to_ticks(self, symbol: str):
        """Subscreve a ticks de um determinado símbolo."""
        req = {"ticks": symbol, "subscribe": 1}
        await self.ws.send(json.dumps(req))

    async def listen(self):
        """Loop principal para escutar mensagens da Deriv."""
        while self.connected and self.ws:
            try:
                # Recebe a mensagem com um timeout para evitar que o listener bloqueie
                message = await asyncio.wait_for(self.ws.recv(), timeout=30) 
                data = json.loads(message)

                if data.get("error"):
                    print(f"[Deriv] ERRO da API: {data['error']['message']}")
                    continue

                msg_type = data.get("msg_type")
                
                # --- PROCESSAMENTO DE DADOS CRÍTICOS (SETANDO EVENTOS) ---
                
                # 1. Autorização
                if msg_type == "authorize" and 'authorize' in data:
                    self.authorized = True
                    account_details = data.get('authorize', {})
                    # Determina se é conta demo ou real
                    if 'is_virtual' in account_details:
                         self.account_info['account_type'] = 'demo' if account_details['is_virtual'] == 1 else 'real'
                    self.auth_event.set() # Sinaliza que a autorização foi processada

                # 2. Informações da Conta (get_settings)
                if msg_type == "get_settings" and 'get_settings' in data:
                    settings = data.get('get_settings', {})
                    if 'currency' in settings:
                         self.account_info['currency'] = settings['currency']
                    if 'email' in settings:
                        # Usa email como nome da conta para o dashboard
                        self.account_info['account_name'] = settings['email'] 
                    self.info_event.set() # Sinaliza que as informações foram processadas
                    
                # 3. Saldos (balance)
                if msg_type == "balance" and 'balance' in data:
                     balance_data = data.get('balance')
                     if balance_data:
                        self.account_info['balance'] = balance_data.get('balance', 0.0)
                        # O saldo pode atualizar a moeda também
                        self.account_info['currency'] = balance_data.get('currency', self.account_info.get('currency', 'USD'))
                        # Garante que o info_event é setado para desbloquear o start()
                        if not self.info_event.is_set():
                            self.info_event.set()
                    
                # 4. Ticks (Atualização da Estratégia)
                if msg_type == "tick":
                    tick = data["tick"]
                    price = float(tick["quote"])
                    update_ticks(price) 
                    print(f"[Deriv] ✅ Tick recebido: {price}") 
                    
                
            except websockets.ConnectionClosed as e:
                print(f"[Deriv] Conexão fechada. Motivo: {e.code} ({e.reason}). Desligando cliente.")
                self.connected = False
                self.authorized = False
                break
            except asyncio.TimeoutError:
                # Envia um 'ping' para manter a conexão viva
                await self.ws.send(json.dumps({"ping": 1}))
                continue
            except Exception as e:
                print(f"[ERRO GERAL] no listener: {e}")
                continue

    async def stop(self):
        """Fecha a conexão."""
        try:
            self.connected = False
            self.authorized = False
            # Limpa os eventos
            self.auth_event.clear()
            self.info_event.clear()
            
            if self.ws:
                await self.ws.close()
        except:
            pass

        print("[Deriv] Cliente parado.")
            
