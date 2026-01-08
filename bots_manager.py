import asyncio
import uuid
from enum import Enum
from typing import Dict, Optional, Any, List
from strategy import generate_signal

class BotState(Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ERROR = "ERROR"

class TradingBot:
    """Representa uma instância de operação do Previus-Starps"""
    def __init__(self, name: str, symbol: str, client: Any):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.symbol = symbol
        self.client = client
        self.state = BotState.ACTIVE
        self.history = []

    async def run_analysis_loop(self):
        """Loop contínuo de análise para este bot específico"""
        while self.state == BotState.ACTIVE:
            sinal = generate_signal()
            if sinal:
                self.history.append(sinal)
                # Aqui o bot enviaria um alerta para o painel
            await asyncio.sleep(2) # Frequência de atualização

class BotsManager:
    """Gerencia todos os bots ativos no sistema"""
    def __init__(self):
        self.active_bots: Dict[str, TradingBot] = {}

    def add_bot(self, name: str, symbol: str, client: Any) -> str:
        novo_bot = TradingBot(name, symbol, client)
        self.active_bots[novo_bot.id] = novo_bot
        return novo_bot.id

    def stop_bot(self, bot_id: str):
        if bot_id in self.active_bots:
            self.active_bots[bot_id].state = BotState.PAUSED

    def get_all_status(self) -> List[Dict]:
        return [
            {"id": b.id, "name": b.name, "state": b.state.value, "symbol": b.symbol}
            for b in self.active_bots.values()
        ]
