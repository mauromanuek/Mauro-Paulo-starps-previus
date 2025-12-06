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
        self._state = BotState.INACTIVE # Inicia INACTIVE, ativado após a conexão
        self.current_run_task: Optional[asyncio.Task] = None

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
        print(f"[Bot {self.id[:4]}] Estado alterado para {new_state.value}")

    # --- 🟢 MÉTODO CRÍTICO: INICIAR EXECUÇÃO 🟢 ---
    def start_loop(self):
        """Inicia a tarefa assíncrona principal do bot (run_bot_loop)."""
        # Verifica se já existe uma task a correr
        if self.current_run_task is None or self.current_run_task.done():
            self._state = BotState.ACTIVE
            # CRÍTICO: Cria a task e a coloca para rodar no loop de eventos
            self.current_run_task = asyncio.create_task(self.run_bot_loop())
            print(f"[Bot {self.id[:4]}] 🟢 Loop de execução iniciado.")
            return True
        else:
            print(f"[Bot {self.id[:4]}] O loop já está ativo.")
            return False

    # --- 🟢 MÉTODO CRÍTICO: PARAR EXECUÇÃO 🟢 ---
    def stop_loop(self):
        """Cancela a tarefa assíncrona do bot."""
        if self.current_run_task and not self.current_run_task.done():
            self.current_run_task.cancel()
            self._state = BotState.INACTIVE
            print(f"[Bot {self.id[:4]}] 🔴 Loop de execução parado.")
            return True
        return False
        
    async def run_bot_loop(self):
        """O loop principal de trading que consulta a estratégia e executa ordens."""
        
        # O loop deve rodar enquanto o cliente Deriv estiver conectado e o bot ativo
        while self.is_active and self.client and self.client.connected:
            try:
                # 1. Obter os indicadores mais recentes (estão em memória no deriv_client)
                indicators = self.client.get_current_indicators() 
                
                # Só processa se houver dados suficientes
                if not indicators:
                    await asyncio.sleep(1)
                    continue

                # 2. Gerar o sinal (CALL, PUT ou None)
                signal = generate_signal(indicators)
                
                # Parâmetros de trading (ajuste-os conforme sua estratégia)
                duration = 5 # Duração da ordem em ticks
                amount = 1.0 # Valor da aposta em USD

                if signal:
                    action = signal['action'] # Ex: 'CALL (COMPRA)' ou 'PUT (VENDA)'
                    
                    # 3. EXECUTAR AÇÃO:
                    if action.startswith("CALL"):
                        print(f"[{self.name}] 🟢 SINAL: COMPRA. Executando ordem...")
                        # ⚠️ ATIVE A LINHA ABAIXO APÓS TESTAR COM DEMO ⚠️
                        # await self.client.buy(self.symbol, duration, amount, "BUY") 
                        
                    elif action.startswith("PUT"):
                        print(f"[{self.name}] 🔴 SINAL: VENDA. Executando ordem...")
                        # ⚠️ ATIVE A LINHA ABAIXO APÓS TESTAR COM DEMO ⚠️
                        # await self.client.buy(self.symbol, duration, amount, "SELL") 
                        
                    # Atrasar o loop para esperar pelo próximo sinal (evita ordens duplicadas imediatas)
                    await asyncio.sleep(60) 
                else:
                    # Se não houver sinal, espera um pouco e tenta novamente
                    await asyncio.sleep(5) 

            except asyncio.CancelledError:
                # A tarefa foi cancelada via stop_loop()
                break
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
        """Retorna todos os bots ativos."""
        return list(self.active_bots.values())

    def stop_all_bots(self):
        """Para o loop de execução de todos os bots."""
        for bot in self.active_bots.values():
            bot.stop_loop()
