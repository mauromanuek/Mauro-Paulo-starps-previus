import asyncio
import websockets
import json
from strategy import update_ticks 

class DerivClient:
    def __init__(self, token: str):
        self.token = token
        self.app_id = "114910"  # Seu App ID configurado
        self.ws = None
        self.connected = False
        self.authorized = False
        self.account_info = {"balance": 0.0, "currency": "USD"}

    async def start(self):
        """Inicia a conexão e mantém o loop vivo"""
        uri = f"wss://ws.derivws.com/websockets/v3?app_id={self.app_id}"
        
        try:
            async with websockets.connect(uri) as websocket:
                self.ws = websocket
                self.connected = True
                print("[Previus-Starps] Conectado ao servidor Deriv.")

                # 1. Autorização
                await self.authorize()
                
                if self.authorized:
                    # 2. Inscrever em Ticks (Volatility 100 como padrão)
                    await self.subscribe_to_ticks("R_100")
                    
                    # 3. Loop de escuta de mensagens
                    await self.listen()
        except Exception as e:
            print(f"[Erro Conexão] {e}")
            self.connected = False

    async def authorize(self):
        """Envia o token para a Deriv validar"""
        auth_data = {"authorize": self.token}
        await self.ws.send(json.dumps(auth_data))
        
        response = await self.ws.recv()
        data = json.loads(response)
        
        if "error" in data:
            print(f"[Erro Auth] {data['error']['message']}")
            self.authorized = False
        else:
            print("[Previus-Starps] Login realizado com sucesso!")
            self.authorized = True
            self.account_info['balance'] = data['authorize'].get('balance', 0.0)

    async def subscribe_to_ticks(self, symbol: str):
        """Pede para a Deriv enviar preços em tempo real"""
        subscribe_msg = {"ticks": symbol, "subscribe": 1}
        await self.ws.send(json.dumps(subscribe_msg))

    async def listen(self):
        """Lê as mensagens que chegam da Deriv continuamente"""
        async for message in self.ws:
            data = json.loads(message)
            
            # Se for um novo preço (tick)
            if data.get("msg_type") == "tick":
                price = float(data["tick"]["quote"])
                # Envia para o 'Cérebro' (strategy.py)
                update_ticks(price)
            
            # Se o saldo mudar, atualiza aqui
            if data.get("msg_type") == "balance":
                self.account_info['balance'] = data['balance']['balance']

    async def disconnect(self):
        """Fecha a conexão com segurança"""
        if self.ws:
            await self.ws.close()
            self.connected = False
            self.authorized = False
