# deriv_client.py
# Deriv websocket client (adaptado para conectar/desconectar on-demand com token passado em runtime)
# Mantém operação em background e fornece on_signal callback quando detectar candidate

import asyncio
import websockets
import json
import uuid
import datetime
from typing import Optional

DERIV_WS_BASE = "wss://ws.derivws.com/websockets/v3?app_id=1089"

class DerivClient:
    def __init__(self, token: Optional[str] = None, on_tick_callback=None):
        self.token = token
        self.on_tick_callback = on_tick_callback
        self.on_signal = None
        self.subscribed_symbols = ["R_100"]
        self._task = None
        self._running = False
        self._ws = None

    def reset(self):
        # limpa estado, sem tocar em token (token pode ser atualizado)
        self._running = False
        self._ws = None
        # do not clear token here; caller controls token lifecycle if needed

    async def stop_async(self):
        # método awaitable para parar a tarefa de run
        self._running = False
        # close websocket if open
        try:
            if self._ws:
                await self._ws.close()
        except Exception:
            pass
        # give some time for loop to end
        await asyncio.sleep(0.2)

    def stop(self):
        # compat layer (sync)
        self._running = False

    async def _authorize(self, ws):
        if not self.token:
            return
        auth = {"authorize": self.token}
        await ws.send(json.dumps(auth))
        # read one response (best-effort)
        try:
            res = await ws.recv()
            try:
                j = json.loads(res)
                # We ignore details in demo; production should validate authorize success
                return j
            except:
                return res
        except Exception:
            return None

    async def _subscribe_ticks(self, ws, symbol):
        msg = {"ticks": symbol, "subscribe": 1}
        await ws.send(json.dumps(msg))

    async def _handle_messages(self, ws):
        async for message in ws:
            try:
                data = json.loads(message)
            except:
                continue

            # handle tick
            if data.get("msg_type") == "tick":
                tick = data.get("tick", {})
                if self.on_tick_callback:
                    try:
                        self.on_tick_callback(tick)
                    except Exception:
                        pass
                # demo rule: if last digit == 7 generate a signal
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
                            "reason": "Último dígito 7 (demo)",
                            "explanation": "Sinal demo emitido pelo deriv_client",
                            "entry": (now + datetime.timedelta(seconds=10)).isoformat() + "Z",
                            "generated_at": now.isoformat() + "Z"
                        }
                        try:
                            self.on_signal(sig)
                        except Exception:
                            pass

    async def run(self):
        # main loop: (re)connect while _running True
        self._running = True
        while self._running:
            try:
                # build URL (no token in URL; token used by authorize message)
                ws_url = DERIV_WS_BASE
                async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as ws:
                    self._ws = ws
                    # authorize if token present
                    if self.token:
                        try:
                            await self._authorize(ws)
                        except Exception:
                            pass
                    # subscribe to symbols
                    for s in self.subscribed_symbols:
                        try:
                            await self._subscribe_ticks(ws, s)
                        except Exception:
                            pass
                    # handle incoming messages
                    await self._handle_messages(ws)
            except Exception:
                # wait then reconnect
                await asyncio.sleep(2.0)
            finally:
                self._ws = None
        # loop end

    # helper to start run in background (non-blocking)
    def start_background(self, loop=None):
        if not loop:
            loop = asyncio.get_event_loop()
        # create background task only if not already running
        if not self._task or self._task.done():
            self._task = loop.create_task(self.run())
        return self._task
