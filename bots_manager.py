import asyncio
import uuid
from enum import Enum
from typing import Dict, Optional, Any, List
from strategy import generate_signal
from executor import TradeExecutor

class BotState(Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ERROR = "ERROR"

class TradingBot:
    def __init__(self, name: str, symbol: str, client: Any):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.symbol = symbol
        self.client = client
        self.executor = TradeExecutor(client)
        self.state = BotState.PAUSED
        self.history = []
        self.stats = {"wins": 0, "losses": 0, "profit": 0.0}

    async def run_auto_loop(self, amount: float):
        """Loop de operação automática real"""
        self.state = BotState.ACTIVE
        while self.state == BotState.ACTIVE:
            signal = generate_signal()
            # Só executa se a probabilidade for alta (conforme config.py)
            if signal and signal.get('probability', 0) >= 0.75:
                await self.executor.execute_trade(signal['action'], amount, self.symbol)
                self.history.append(signal)
            await asyncio.sleep(60) # Espera 1 minuto por vela

class BotsManager:
    def __init__(self):
        self.active_bots: Dict[str, TradingBot] = {}

    def add_bot(self, name: str, symbol: str, client: Any) -> str:
        novo_bot = TradingBot(name, symbol, client)
        self.active_bots[novo_bot.id] = novo_bot
        return novo_bot.id

    def stop_bot(self, bot_id: str):
        if bot_id in self.active_bots:
            self.active_bots[bot_id].state = BotState.PAUSED
