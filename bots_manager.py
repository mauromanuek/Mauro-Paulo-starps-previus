# bots_manager.py

import asyncio
import uuid
from enum import Enum
from typing import Dict, Optional, Any, List 
import time
from strategy import generate_signal # Requer que strategy.py esteja correto

class BotState(Enum):
    """Estados possíveis para um bot."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PAUSED = "PAUSED"

class TradingBot:
    """Representa uma instância de um bot de trading automático."""
    
    def __init__(self, name: str, symbol: str, tf: str, stop_loss: float, take_profit: float, client: Any):
        self.id = str(uuid.uuid4())
        self.name = name
        self.symbol = symbol
        self.tf = tf
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.client = client
        self._state = BotState.ACTIVE
        self.current_run_task = None

    @property
    def is_active(self) -> bool:
        """Verifica se o bot está ativo."""
        return self._state == BotState.ACTIVE

    @property
    def state(self) -> BotState:
        """Retorna o estado atual do bot."""
        return self._state

    @state.setter
    def state(self, new_state: BotState):
        """Define um novo estado para o bot."""
        self._state = new_state
        print(f"[Bot {self.id[:4]}] Estado alterado para: {new_state.value}")

    def to_dict(self) -> Dict[str, Any]:
        """Retorna os dados do bot para o frontend."""
        return {
            "id": self.id,
            "name": self.name,
            "symbol": self.symbol,
            "tf": self.tf,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "state": self.state.value
        }

    async def run_bot_loop(self):
        """Loop principal que verifica sinais e executa operações."""
        if self.current_run_task and not self.current_run_task.done():
            print(f"[Bot {self.id[:4]}] Aviso: Loop já está a correr. Não a iniciar novamente.")
            return

        print(f"[Bot {self.id[:4]}] Loop iniciado para {self.symbol}@{self.tf}min.")
        
        while self.is_active and self.client and self.client.authorized:
            try:
                # 1. Obter o sinal da estratégia
                signal = generate_signal(self.symbol, self.tf)
                
                if signal and signal['action']:
                    action = signal['action']
                    
                    print(f"[Bot {self.id[:4]}] 🟢 SINAL ENCONTRADO: {action} em {self.symbol} com Prob: {signal['probability']:.0f}%")
                    
                    # --- LÓGICA DE EXECUÇÃO DE TRADE (SIMULAÇÃO) ---
                    # **Aqui você faria a chamada para o cliente Deriv para executar a ordem real**
                    # Ex: await self.client.buy(self.symbol, 5, 1.0, action) # Duração de 5 ticks, valor de $1.0
                    
                    # SIMULAÇÃO DE TRADE
                    print(f"[Bot {self.id[:4]}] TRADE EXECUTADO: {action} (SL: ${self.stop_loss}, TP: ${self.take_profit})")
                    
                    # Atrasar o loop para esperar pelo próximo sinal
                    await asyncio.sleep(60) # Espera 1 minuto após um sinal (simulação)
                else:
                    # Se não houver sinal, espera um pouco e tenta novamente
                    await asyncio.sleep(5) 

            except Exception as e:
                print(f"[ERRO Bot {self.id[:4]}] Erro no loop: {e}")
                await asyncio.sleep(10) # Espera mais em caso de erro

        print(f"[Bot {self.id[:4]}] Loop finalizado.")


class BotsManager:
    """Gerencia todas as instâncias de bots de trading."""
    
    def __init__(self):
        self.active_bots: Dict[str, TradingBot] = {}

    def create_bot(self, name: str, symbol: str, tf: str, stop_loss: float, take_profit: float, client: Any) -> TradingBot:
        """Cria e registra um novo bot."""
        bot = TradingBot(name, symbol, tf, stop_loss, take_profit, client)
        self.active_bots[bot.id] = bot
        print(f"[Manager] Novo bot criado: {bot.id}")
        return bot

    def get_bot(self, bot_id: str) -> Optional[TradingBot]:
        """Busca um bot pelo ID."""
        return self.active_bots.get(bot_id)

    def get_all_bots(self) -> List[TradingBot]:
        """Retorna uma lista de todos os bots."""
        return list(self.active_bots.values())

    def start_all_bots(self):
        """
        🚨 NOVO: Inicia ou reinicia o loop para todos os bots definidos como ACTIVE.
        Chamado após uma reconexão bem-sucedida à Deriv.
        """
        for bot in self.active_bots.values():
            # CRÍTICO: Só inicia o loop se o bot estiver ativo.
            if bot.is_active: 
                # Cria uma tarefa assíncrona para executar o loop do bot
                bot.current_run_task = asyncio.create_task(bot.run_bot_loop())
                print(f"[Manager] Bot {bot.id[:4]} relançado.")
