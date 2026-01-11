import asyncio
import websockets
import json
from strategy import update_ticks

class DerivClient:
    def __init__(self, token: str):
        self.token = token
        self.ws = None
        self.authorized = False
        self.connected = False
        self.account_info = {"balance": 0.0, "account_type": "demo"}

    async def start(self):
        uri = "wss://ws.derivws.com/websockets/v3?app_id=1089" # App ID padrão
        try:
            async with websockets.connect(uri) as websocket:
                self.ws = websocket
                self.connected = True
                
                # Autorizar
                await self.ws.send(json.dumps({"authorize": self.token}))
                
                async for message in self.ws:
                    data = json.loads(message)
                    
                    if "authorize" in data:
                        if "error" in data:
                            self.authorized = False
                            break
                        self.authorized = True
                        self.account_info["balance"] = data["authorize"]["balance"]
                        self.account_info["account_type"] = "real" if not data["authorize"]["is_virtual"] else "demo"
                        # Subscrever Ticks
                        await self.ws.send(json.dumps({"ticks": "R_100", "subscribe": 1}))
                    
                    if "tick" in data:
                        update_ticks(data["tick"]["quote"])
                        
                    if "error" in data:
                        print(f"Erro Deriv: {data['error']['message']}")
        except Exception as e:
            self.connected = False
            print(f"Erro Conexão: {e}")
