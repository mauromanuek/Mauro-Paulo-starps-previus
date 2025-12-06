# deriv_client.py 

import asyncio
import websockets
import json
from datetime import datetime
from strategy import update_ticks 
from typing import Dict, Any, Optional, Set

class DerivClient:
    
    # SEU APP ID INSERIDO AQUI
    APP_ID = "114910" 
    WS_URL = f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}"

    def __init__(self, token: str):
        self.token = token
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.authorized = False
        self.account_info: Dict[str, Any] = {"balance": 0.0, "account_type": "demo", "currency": "USD", "account_name": "N/A"}
        
        # 🟢 CRÍTICO: Eventos para esperar respostas da API de forma não-bloqueante
        self.auth_event = asyncio.Event() 
        self.info_event = asyncio.Event() 
        
        # 🚀 NOVO: Conjunto de Queues para transmitir ticks aos clientes de front-end (navegadores)
        self.tick_listeners: Set[asyncio.Queue] = set() 

    # -----------------------------------------------------------
    # MÉTODOS DE GESTÃO DE LISTENERS DE FRONT-END
    # -----------------------------------------------------------
    async def subscribe_tick_listener(self, queue: asyncio.Queue):
        """Adiciona uma queue para receber os novos ticks."""
        self.tick_listeners.add(queue)

    def unsubscribe_tick_listener(self, queue: asyncio.Queue):
        """Remove uma queue."""
        self.tick_listeners.discard(queue)

    async def broadcast_tick(self, price: float):
        """Envia o novo tick para todas as queues inscritas."""
        # Envia a mensagem no formato JSON esperado pelo front-end
        tick_message = json.dumps({"type": "tick", "price": price})
        
        # Cria uma cópia da lista de listeners para iterar com segurança
        for queue in list(self.tick_listeners): 
            try:
                # put_nowait garante que não bloqueamos o loop principal da Deriv
                queue.put_nowait(tick_message) 
            except asyncio.QueueFull:
                # Se a queue estiver cheia, o cliente está lento/desligado. Remove-o.
                print("[Deriv] Aviso: Queue de tick cheia. Removendo listener lento.")
                self.unsubscribe_tick_listener(queue)
    # -----------------------------------------------------------

    async def start(self):
        """Inicia a conexão completa com a Deriv e espera pelos dados da conta."""
        try:
            self.ws = await websockets.connect(self.WS_URL)
            print("[Deriv] Conexão WebSocket aberta.")
            self.connected = True
            
            # 1. CRÍTICO: Inicia o listener ANTES de enviar requisições
            asyncio.create_task(self.listen())
            print("[Deriv] Tarefa de listener iniciada.")

            # 2. Autorização (espera o evento ser setado no listener)
            await self.authorize()
            await asyncio.wait_for(self.auth_event.wait(), timeout=10) 
            
            if not self.authorized:
                raise Exception("Autorização falhou.")

            print("[Deriv] Token autorizado com sucesso. O bot está ONLINE.")
            
            # 3. Informações da Conta (espera o evento ser setado no listener)
            await self.get_account_info() 
            await asyncio.wait_for(self.info_event.wait(), timeout=10) 
            print("[Deriv] DEBUG: Informações da conta processadas.") 
                
            # 4. Subscrição de Ticks (agora o listener está ativo para recebê-los)
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
        await self.ws.send(json.dumps({"balance": 1, "subscribe": 1}))
        await self.ws.send(json.dumps({"get_settings": 1}))
    
    async def subscribe_to_ticks(self, symbol: str):
        """Subscreve a ticks de um determinado símbolo."""
        req = {"ticks": symbol, "subscribe": 1}
        await self.ws.send(json.dumps(req))

    async def listen(self):
        """Loop principal para escutar mensagens da Deriv."""
        print("[Deriv] Iniciando listener de ticks…")
        while self.connected and self.ws:
            try:
                message = await asyncio.wait_for(self.ws.recv(), timeout=30) 
                data = json.loads(message)

                if data.get("error"):
                    print(f"[Deriv] ERRO da API: {data['error']['message']}")
                    continue

                msg_type = data.get("msg_type")
                
                # --- PROCESSAMENTO DE AUTORIZAÇÃO E INFORMAÇÕES DE CONTA ---
                
                if msg_type == "authorize" and 'authorize' in data:
                    self.authorized = True
                    account_details = data.get('authorize', {})
                    if 'is_virtual' in account_details:
                         self.account_info['account_type'] = 'demo' if account_details['is_virtual'] == 1 else 'real'
                    self.auth_event.set()

                if msg_type == "get_settings" and 'get_settings' in data:
                    settings = data.get('get_settings', {})
                    if 'currency' in settings:
                         self.account_info['currency'] = settings['currency']
                    if 'email' in settings:
                        self.account_info['account_name'] = settings['email'] 
                    if self.account_info.get('balance') is not None:
                        self.info_event.set()
                    
                if msg_type == "balance" and 'balance' in data:
                     balance_data = data.get('balance')
                     if balance_data:
                        self.account_info['balance'] = balance_data.get('balance', 0.0)
                        self.account_info['currency'] = balance_data.get('currency', self.account_info.get('currency', 'USD'))
                        if not self.info_event.is_set():
                            self.info_event.set()
                    
                # 4. Ticks (Atualização da Estratégia E BROADCAST para o Front-end)
                if msg_type == "tick":
                    tick = data["tick"]
                    price = float(tick["quote"])
                    
                    # 1. Atualiza a história de ticks da Estratégia
                    update_ticks(price) 
                    
                    # 2. 🚀 Transmite o tick para todos os navegadores conectados
                    await self.broadcast_tick(price) 
                    
                    print(f"[Deriv] ✅ Tick recebido: {price}") 
                    
                
            except websockets.ConnectionClosed as e:
                print(f"[Deriv] Conexão fechada. Motivo: {e.code} ({e.reason}). Desligando cliente.")
                self.connected = False
                self.authorized = False
                break
            except asyncio.TimeoutError:
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
            self.auth_event.clear()
            self.info_event.clear()
            # 🛑 CRÍTICO: Limpa todos os listeners de front-end
            self.tick_listeners.clear() 
            
            if self.ws:
                await self.ws.close()
        except:
            pass

        print("[Deriv] Cliente parado.")
