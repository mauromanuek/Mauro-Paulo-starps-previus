# bots_manager.py

import asyncio
import uuid
import httpx 
import time
from typing import Dict, Any, Optional, List
from deriv_client import DerivClient # Importa para tipagem

# URL base do servidor (usamos localhost na porta do Uvicorn para chamada interna no Render)
SIGNAL_URL = "http://localhost:10000/signal" 

# --- Estrutura de Bot ---
class BotState:
    
    def __init__(self, name: str, symbol: str, timeframe: str, sl: float, tp: float, client: DerivClient):
        self.id = str(uuid.uuid4())
        self.name = name
        self.symbol = symbol
        self.timeframe = timeframe
        self.sl = sl
        self.tp = tp
        self.is_active = False
        self.task: Optional[asyncio.Task] = None
        self.client = client 

    def to_dict(self):
        """Serializa o estado do bot para o frontend."""
        return {
            "id": self.id,
            "name": self.name,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "sl": self.sl,
            "tp": self.tp,
            "is_active": self.is_active,
        }

    async def get_signal_from_api(self) -> Optional[Dict[str, Any]]:
        """CORREÇÃO: Chama a rota /signal do próprio servidor via HTTP (httpx)."""
        async with httpx.AsyncClient() as client:
            try:
                # Remove 'm' se estiver no timeframe para usar como int
                tf_int = self.timeframe.replace('m', '')
                params = {"symbol": self.symbol, "tf": tf_int}
                
                response = await client.get(
                    SIGNAL_URL,
                    params=params,
                    timeout=10
                )

                if response.status_code == 200:
                    return response.json()
                
                elif response.status_code == 404:
                    return None # Sinal não pronto
                
                else:
                    print(f"[Bot {self.id[:4]}] ERRO HTTP! Status: {response.status_code}. Mensagem: {response.text}")
                    return None

            except httpx.ConnectError:
                print(f"[Bot {self.id[:4]}] ERRO HTTP: Falha de conexão a {SIGNAL_URL}")
                return None
            
            except Exception as e:
                print(f"[Bot {self.id[:4]}] ERRO INESPERADO: {e}")
                return None

    async def run_bot_loop(self):
        """Loop principal de execução do bot."""
        while self.is_active:
            try:
                # 1. Obter sinal da API (via HTTP)
                signal = await self.get_signal_from_api()

                if signal and signal.get('action') and signal['action'] != 'AGUARDANDO':
                    action = signal['action'].split(' ')[0]
                    
                    print(f"[Bot {self.id[:4]}] -> SINAL {action} em {self.symbol}!")
                    
                    # ⚠️ Aqui você deve colocar a lógica real de execução de ordem da Deriv
                    
                    # Espera 1 minuto após a execução
                    await asyncio.sleep(60) 
                else:
                    # Espera 5 segundos para o próximo cálculo
                    await asyncio.sleep(5) 

            except asyncio.CancelledError:
                print(f"[Bot {self.id[:4]}] Loop cancelado.")
                break
            except Exception as e:
                print(f"[Bot {self.id[:4]}] Erro fatal no loop: {e}")
                await asyncio.sleep(10)


class BotsManager:
    """Gerencia todas as instâncias de bots de trading."""
    
    def __init__(self):
        self.bots: Dict[str, BotState] = {}

    def create_bot(self, name: str, symbol: str, timeframe: str, sl: float, tp: float, client: DerivClient) -> BotState:
        """Cria e registra um novo bot."""
        bot = BotState(name, symbol, timeframe, sl, tp, client)
        self.bots[bot.id] = bot
        print(f"[Manager] Novo bot criado: {bot.id}")
        return bot

    def get_all_bots(self) -> List[BotState]:
        """Retorna uma lista de todos os BotState."""
        return list(self.bots.values())

    def activate_bot(self, bot_id: str):
        bot = self.bots.get(bot_id)
        if not bot or bot.is_active:
            return False

        bot.is_active = True
        bot.task = asyncio.create_task(bot.run_bot_loop())
        print(f"[Manager] Bot ATIVADO: {bot.name}")
        return True

    def deactivate_bot(self, bot_id: str):
        bot = self.bots.get(bot_id)
        if not bot or not bot.is_active:
            return False

        bot.is_active = False
        if bot.task:
            bot.task.cancel()
        print(f"[Manager] Bot DESATIVADO: {bot.name}")
        return True

manager = BotsManager()
        
