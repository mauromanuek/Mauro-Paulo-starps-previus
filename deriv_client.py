import asyncio
import websockets
import json
import pandas as pd
from config import APP_ID

class DerivClient:
    def __init__(self):
        self.uri = f"wss://ws.binaryws.com/websockets/v3?app_id={APP_ID}"
        self.ws = None
        self.ticks = []

    async def connect(self):
        self.ws = await websockets.connect(self.uri)
        return self.ws

    async def authorize(self, token):
        await self.ws.send(json.dumps({"authorize": token}))
        res = await self.ws.recv()
        return json.loads(res)

    async def subscribe_ticks(self, symbol):
        await self.ws.send(json.dumps({"ticks": symbol, "subscribe": 1}))
        
    async def get_account_info(self):
        await self.ws.send(json.dumps({"balance": 1, "subscribe": 1}))
        res = await self.ws.recv()
        return json.loads(res)

client = DerivClient()
