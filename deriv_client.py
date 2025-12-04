# deriv_client.py
# Cliente WebSocket da Deriv — versão simplificada
# Recebe ticks e gera EVENTOS DE SINAL (DEMO)
# IA real substitui lógica futura.

import asyncio
import websockets
import json
import uuid
import datetime

DERIV_WS = "wss://ws.derivws.com/websockets/v3?app_id=1089"

class DerivClient:

    def __init__(self, token=None, on_tick_callback=None):
        self.token = token
        self.on_tick_callback = on_tick_callback
        self.on_signal = None
        self.subscribed_symbols = ["R_100"]
        self._running = False
        self._ws = None

    async def _authorize(self, ws):
        if not self.token:
            return
        await ws.send(json.dumps({"authorize": self.token}))
        await ws.recv()  # resposta ignorada no demo

    async def _subscribe(self, ws, symbol):
        await ws.send(json.dumps({"ticks": symbol, "subscribe": 1}))

    async def _handle_messages(self, ws):

        async for msg in ws:
            try:
                data = json.loads(msg)
            except:
                continue

            if data.get("msg_type") == "tick":
                tick = data.get("tick", {})

                # repassar tick
                if self.on_tick_callback:
                    self.on_tick_callback(tick)

                # ⚠️ regra demo: último dígito == 7 → envia sinal
                quote = tick.get("quote")
                if quote is not None:
                    try:
                        last_digit = int(str(quote)[-1])
                    except:
                        last_digit = None

                    if last_digit == 7 and self.on_signal:
                        now = datetime.datetime.utcnow()
                        sig = {
                            "id": str(uuid.uuid4()),
                            "symbol": tick.get("symbol"),
                            "tf": 60,
                            "action": "CALL",
                            "probability": 0.78,
                            "reason": "Último dígito 7 (DEMO)",
                            "explanation": "Sinal demonstrativo do deriv_client.",
                            "entry": (now + datetime.timedelta(seconds=10)).isoformat() + "Z",
                            "generated_at": now.isoformat() + "Z"
                        }
                        self.on_signal(sig)

    async def run(self):
        self._running = True

        while self._running:
            try:
                async with websockets.connect(DERIV_WS) as ws:
                    self._ws = ws

                    # autorizar
                    await self._authorize(ws)

                    # subscrever símbolos
                    for s in self.subscribed_symbols:
                        await self._subscribe(ws, s)

                    # ler mensagens
                    await self._handle_messages(ws)

            except Exception:
                await asyncio.sleep(2)

            finally:
                self._ws = None

    def stop(self):
        self._running = False
