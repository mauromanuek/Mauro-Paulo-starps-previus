import asyncio
import websockets
import json
from strategy import update_ticks

class DerivClient:
    APP_ID = "114910" 

    def __init__(self, token: str):
        self.token = token
        self.ws = None
        self.authorized = False
        self.account_info = {"balance": 0.0, "account_type": "demo"}

    async def start(self):
        uri = f"wss://ws.derivws.com/websockets/v3?app_id={self.APP_ID}"
        try:
            async with websockets.connect(uri) as websocket:
                self.ws = websocket
                await self.ws.send(json.dumps({"authorize": self.token}))
                async for message in self.ws:
                    data = json.loads(message)
                    if "authorize" in data:
                        if "error" in data: break
                        self.authorized = True
                        self.account_info["balance"] = data["authorize"]["balance"]
                        self.account_info["account_type"] = "real" if not data["authorize"]["is_virtual"] else "demo"
                        await self.ws.send(json.dumps({"ticks": "R_100", "subscribe": 1}))
                    if "tick" in data:
                        update_ticks(data["tick"]["quote"])
        except Exception as e:
            print(f"Erro: {e}")
