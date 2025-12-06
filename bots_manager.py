# bots_manager.py

import asyncio
import uuid
from enum import Enum
from typing import Dict, Optional, Any, List 
import time
from strategy import generate_signal, calculate_indicators # Requer que strategy.py esteja correto

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
        self.tf = int(tf) # Tempo de ciclo do bot em Ticks (baseado na sua TF do frontend)
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.client = client
        self._state = BotState.INACTIVE
        self.current_run_task: Optional[asyncio.Task] = None
        
        self.stats = {"trades": 0, "wins": 0, "losses": 0}

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
        """Define um novo estado para o bot e gere a task."""
        self._state = new_state
        print(f"[Bot {self.id[:4]}] Estado alterado para {new_state.name}")
        
        if new_state == BotState.ACTIVE and self.current_run_task is None:
            self.current_run_task = asyncio.create_task(self.run_loop())
        elif new_state != BotState.ACTIVE and self.current_run_task:
            self.current_run_task.cancel()
            self.current_run_task = None
    
    async def run_loop(self):
        """Loop principal de execução do bot."""
        print(f"[Bot {self.id[:4]}] Loop iniciado. Ciclo: {self.tf} ticks.")

        while self.is_active:
            try:
                # 1. Espera pelo ciclo (o tempo é em segundos, mas usamos como ciclo de ticks para simplificar)
                # O loop irá correr a cada self.tf segundos (simulando a espera por X ticks)
                await asyncio.sleep(self.tf) 

                # 2. Gera o sinal (a função de estratégia lê o histórico global)
                indicators = calculate_indicators()
                if not indicators:
                    print(f"[Bot {self.id[:4]}] Dados insuficientes para análise. Esperando...")
                    continue
                    
                signal_data = generate_signal(indicators)
                
                if signal_data and signal_data.get("action"):
                    action = signal_data["action"].split(' ')[0] # Ex: 'CALL' de 'CALL (COMPRA)'
                    
                    # --- EXECUÇÃO REAL NA DERIV ---
                    duration = 5 # Duração da operação em Ticks (5 ticks é padrão)
                    amount = 1.00 # Aposta padrão de $1.00
                    
                    print(f"[Bot {self.id[:4]}] SINAL: {action}. Executando trade...")

                    contract = await self.client.buy(
                        symbol=self.symbol, 
                        duration=duration, 
                        amount=amount, 
                        action=action
                    )
                    
                    if contract:
                        self.stats["trades"] += 1
                        print(f"[Bot {self.id[:4]}] ORDEM SUCESSO. Contrato ID: {contract['contract_id']}")
                    else:
                        print(f"[Bot {self.id[:4]}] ORDEM FALHOU. {signal_data.get('reason', 'Erro desconhecido.')}")
                        
                    # Espera um pouco após o trade para evitar limites da API
                    await asyncio.sleep(duration + 1) 

                else:
                    # Sem sinal, espera o próximo ciclo
                    print(f"[Bot {self.id[:4]}] Sem sinal: {signal_data.get('reason', 'Nenhuma condição acionada.')}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ERRO Bot {self.id[:4]}] Erro no loop: {e}")
                await asyncio.sleep(10) # Espera mais em caso de erro

        print(f"[Bot {self.id[:4]}] Loop finalizado.")


class BotsManager:
    """Gerencia todas as instâncias de bots de trading."""
    
    def __init__(self):
        self.active_bots: Dict[str, TradingBot] = {}
        self.client: Optional[DerivClient] = None

    def set_client(self, client: DerivClient):
        """Define a instância do DerivClient após o login."""
        self.client = client
        
    def create_bot(self, name: str, symbol: str, tf: str, stop_loss: float, take_profit: float, client: Any) -> TradingBot:
        """Cria e registra um novo bot."""
        bot = TradingBot(name, symbol, tf, stop_loss, take_profit, client)
        self.active_bots[bot.id] = bot
        print(f"[Manager] Novo bot criado: {bot.id}")
        return bot

    def toggle_bot_state(self, bot_id: str, new_state: BotState) -> bool:
        """Muda o estado do bot (Ativar/Desativar)."""
        bot = self.active_bots.get(bot_id)
        if bot:
            bot.state = new_state
            return True
        return False
        
    def get_all_bots_info(self) -> List[Dict[str, Any]]:
        """Lista todos os bots e o seu estado para o frontend."""
        out = []
        for bot_id, bot in self.active_bots.items():
            out.append({
                "id": bot_id,
                "name": bot.name,
                "symbol": bot.symbol,
                "tf": bot.tf,
                "stop_loss": bot.stop_loss,
                "take_profit": bot.take_profit,
                "state": bot.state.name,
                "stats": bot.stats,
            })
        return out
