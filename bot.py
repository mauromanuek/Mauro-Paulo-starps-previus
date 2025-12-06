import asyncio
import random
from collections import deque
from strategy import generate_signal

class Bot:
    def __init__(self, bot_id, spec, deriv):
        self.id = bot_id
        self.spec = spec
        self.deriv = deriv

        self.symbol = spec.get("symbol", "R_100")
        self.tf = int(spec.get("tf", 60))
        self.policy = spec.get("policy", "conservative")

        self.active = False
        self.closes = deque(maxlen=300)
        self.stats = {"trades": 0, "wins": 0, "losses": 0}

        self._task = None
        self._original_tick_cb = None

    async def _on_tick(self, tick):
        if tick["symbol"] == self.symbol:
            self.closes.append(float(tick["quote"]))

    async def loop(self):
        # subscrever símbolo
        await self.deriv.subscribe(self.symbol)

        # capturar callback anterior
        self._original_tick_cb = self.deriv.on_tick
        self.deriv.on_tick = lambda t: asyncio.create_task(self._on_tick(t))

        while self.active:
            await asyncio.sleep(self.tf)

            closes = list(self.closes)
            action, prob, reason = generate_signal(closes, self.policy)

            if not action:
                print(f"[Bot {self.id}] Sem sinal: {reason}")
                continue

            # Simulação de trade
            self.stats["trades"] += 1
            win = random.random() < prob

            if win:
                self.stats["wins"] += 1
            else:
                self.stats["losses"] += 1

            print(f"[Bot {self.id}] {action} | prob={prob} | WIN={win} | {reason}")

        # restaurar callback original
        self.deriv.on_tick = self._original_tick_cb

    def start(self):
        if not self.active:
            self.active = True
            loop = asyncio.get_event_loop()
            self._task = loop.create_task(self.loop())

    async def stop(self):
        self.active = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except:
                pass
