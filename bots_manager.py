# bots_manager.py - VERSÃO FINAL ESTÁVEL E ROBUSTA

import asyncio
import uuid
import httpx # 🟢 ESSENCIAL PARA COMUNICAÇÃO INTERNA
from enum import Enum
from typing import Dict, Optional, Any, List 
from deriv_client import DerivClient # Importa para tipagem

# 🟢 CORREÇÃO CRÍTICA: URL para ligar para a rota /signal do próprio servidor
SIGNAL_URL = "http://localhost:10000/signal" 

class BotState(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PAUSED = "PAUSED"

class TradingBot:
    
    def __init__(self, name: str, symbol: str, tf: str, stop_loss: float, take_profit: float, client: DerivClient):
        self.id = str(uuid.uuid4())
        self.name = name
        self.symbol = symbol
        self.tf = tf
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.client = client
        self._state = BotState.ACTIVE
        self.current_run_task: Optional[asyncio.Task] = None

    @property
    def is_active(self) -> bool:
        return self._state == BotState.ACTIVE

    @property
    def state(self) -> BotState:
        return self._state

    @state.setter
    def state(self, new_state: BotState):
        self._state = new_state
        print(f"[Bot {self.id[:4]}] Estado alterado para {new_state.value}")
        if new_state == BotState.INACTIVE and self.current_run_task:
            self.current_run_task.cancel()
            self.current_run_task = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "symbol": self.symbol,
            "tf": self.tf,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "is_active": self.is_active,
            "status": self.state.value
        }

    async def get_signal_from_api(self) -> Optional[Dict[str, Any]]:
        """Chama a rota /signal do próprio servidor via HTTP."""
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                # Remove 'm' se estiver no timeframe para usar como int
                tf_int = self.tf.replace('m', '')
                params = {"symbol": self.symbol, "tf": tf_int}
                
                response = await client.get(SIGNAL_URL, params=params)

                if response.status_code == 200:
                    return response.json()
                
                elif response.status_code == 404:
                    return None # Sinal não pronto (dados insuficientes)
                
                else:
                    print(f"[Bot {self.id[:4]}] ERRO HTTP! Status: {response.status_code}. Mensagem: {response.text}")
                    return None

            except Exception as e:
                print(f"[Bot {self.id[:4]}] ERRO INESPERADO ao ligar para /signal: {e}")
                return None

    async def run_bot_loop(self):
        
        self.current_run_task = asyncio.current_task()

        while self.is_active:
            try:
                # 1. Obter sinal da API (via HTTP)
                signal = await self.get_signal_from_api()

                if signal and signal.get('action') and signal['action'] != 'AGUARDANDO':
                    action = signal['action'].split(' ')[0]
                    
                    print(f"[Bot {self.id[:4]}] -> SINAL RECEBIDO: {action} em {self.symbol}!")
                    
                    # 2. Simulação de execução de ordem (substituir por API real da Deriv)
                    print(f"[Bot {self.id[:4]}] -> EXECUTANDO ORDEM: {action}")
                    
                    await asyncio.sleep(60) 
                else:
                    await asyncio.sleep(5) 

            except asyncio.CancelledError:
                print(f"[Bot {self.id[:4]}] Loop cancelado.")
                break
            except Exception as e:
                print(f"[ERRO Bot {self.id[:4]}] Erro fatal no loop: {e}")
                await asyncio.sleep(10)


class BotsManager:
    """Gerencia todas as instâncias de bots de trading."""

    def __init__(self):
        self.active_bots: Dict[str, TradingBot] = {}

    def create_bot(self, name: str, symbol: str, tf: str, stop_loss: float, take_profit: float, client: DerivClient) -> TradingBot:
        """Cria e registra um novo bot."""
        bot = TradingBot(name, symbol, tf, stop_loss, take_profit, client)
        self.active_bots[bot.id] = bot
        print(f"[Manager] Novo bot criado: {bot.id}")
        return bot

    def get_bot(self, bot_id: str) -> Optional[TradingBot]:
        return self.active_bots.get(bot_id)

    def get_all_bots(self) -> List[TradingBot]:
        return list(self.active_bots.values())

    def activate_bot(self, bot_id: str):
        bot = self.active_bots.get(bot_id)
        if not bot or bot.is_active:
            return False

        bot.state = BotState.ACTIVE
        bot.current_run_task = asyncio.create_task(bot.run_bot_loop())
        print(f"[Manager] Bot ATIVADO: {bot.name}")
        return True

    def deactivate_bot(self, bot_id: str):
        bot = self.active_bots.get(bot_id)
        if not bot or not bot.is_active:
            return False

        bot.state = BotState.INACTIVE
        print(f"[Manager] Bot DESATIVADO: {bot.name}")
        return True

# Exporta a instância única do manager
manager = BotsManager()
    
