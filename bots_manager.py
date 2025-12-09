# bots_manager.py - Gerencia a instância de cada bot de trading

import uuid
import asyncio
from enum import Enum
from typing import Optional, Dict, List, Any, TYPE_CHECKING
import time

# Apenas para tipagem
if TYPE_CHECKING:
    from deriv_client import DerivClient

# Enum para o estado do bot
class BotState(str, Enum):
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"

class TradingBot:
    """Representa uma única instância de bot de trading."""
    
    def __init__(self, name: str, symbol: str, tf: str, sl: float, tp: float, client: 'DerivClient'):
        self.id = str(uuid.uuid4())
        self.name = name
        self.symbol = symbol
        self.tf = tf
        self.stop_loss = sl
        self.take_profit = tp
        self.client = client
        self.state: BotState = BotState.RUNNING
        self.current_run_task: Optional[asyncio.Task] = None
        self.trades_count = 0
        
    async def run_loop(self):
        """Loop de execução principal (simulação)."""
        print(f"Bot {self.name} iniciado.")
        try:
            while self.state == BotState.RUNNING:
                await asyncio.sleep(5) # Espera passiva
        except asyncio.CancelledError:
            print(f"Bot {self.name} loop cancelado.")
        finally:
            self.state = BotState.STOPPED
            print(f"Bot {self.name} parado.")

    async def execute_trade(self, signal: Dict[str, Any]):
        """Simula a execução de uma ordem (seria a API de trading real)."""
        if self.state != BotState.RUNNING:
            print(f"Bot {self.name} pausado, ignorando sinal.")
            return

        print(f"[{self.name}] 🚀 Executando trade: {signal['action']} em {signal['symbol']}")
        self.trades_count += 1
        
        await asyncio.sleep(0.5) 
        print(f"[{self.name}] ✅ Ordem enviada com SL={self.stop_loss} e TP={self.take_profit}")


class BotsManager:
    """Gerencia todas as instâncias ativas do TradingBot."""
    
    def __init__(self):
        self.bots: Dict[str, TradingBot] = {}
        
    def create_bot(self, name: str, symbol: str, tf: str, sl: float, tp: float, client: 'DerivClient') -> TradingBot:
        """Cria e regista um novo bot."""
        new_bot = TradingBot(name, symbol, tf, sl, tp, client)
        self.bots[new_bot.id] = new_bot
        return new_bot

    def get_bot(self, bot_id: str) -> Optional[TradingBot]:
        """Retorna um bot pelo ID."""
        return self.bots.get(bot_id)

    def get_all_bots(self) -> List[TradingBot]:
        """Retorna uma lista de todos os bots."""
        return list(self.bots.values())

    async def process_signal(self, signal: Dict[str, Any]):
        """Envia o sinal de trading para todos os bots ativos."""
        for bot in self.bots.values():
            if bot.state == BotState.RUNNING and bot.symbol == signal['symbol'] and bot.tf == signal['tf']:
                # Cria uma tarefa de fundo para não bloquear o listener principal
                asyncio.create_task(bot.execute_trade(signal))
