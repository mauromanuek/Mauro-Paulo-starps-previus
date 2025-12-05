# bots_manager.py

import asyncio
import uuid
import httpx # Importação da biblioteca HTTP
from typing import Dict, Any, Optional

# URL base do servidor (usamos localhost porque é uma chamada interna)
# Se o Render estiver a bloquear a chamada por 'localhost', o endereço IP interno
# ou a URL externa teriam que ser usados, mas vamos começar pelo padrão:
SIGNAL_URL = "http://127.0.0.1:10000/signal" 


class BotState:
    def __init__(self, name: str, symbol: str, timeframe: int, sl: float, tp: float):
        self.id = str(uuid.uuid4())
        self.name = name
        self.symbol = symbol
        self.timeframe = timeframe
        self.sl = sl
        self.tp = tp
        self.is_active = False
        self.task: Optional[asyncio.Task] = None


class BotsManager:
    def __init__(self):
        self.bots: Dict[str, BotState] = {}
        self.http_client = httpx.AsyncClient()


    def create_bot(self, name: str, symbol: str, timeframe: int, sl: float, tp: float) -> BotState:
        new_bot = BotState(name, symbol, timeframe, sl, tp)
        self.bots[new_bot.id] = new_bot
        print(f"[BotsManager] Bot Criado: {new_bot.name} ({new_bot.id[:4]})")
        return new_bot

    def activate_bot(self, bot_id: str):
        if bot_id not in self.bots:
            return False

        bot = self.bots[bot_id]

        if not bot.is_active:
            bot.is_active = True
            
            # Cria a tarefa de loop do bot em segundo plano
            bot.task = asyncio.create_task(self.run_bot_loop(bot))
            print(f"[BotsManager] Bot ATIVADO: {bot.name}")
            return True
        return False

    def deactivate_bot(self, bot_id: str):
        if bot_id not in self.bots:
            return False

        bot = self.bots[bot_id]

        if bot.is_active:
            bot.is_active = False
            if bot.task:
                bot.task.cancel() # Cancela a tarefa de loop
            print(f"[BotsManager] Bot DESATIVADO: {bot.name}")
            return True
        return False

    async def get_signal_from_api(self, bot: BotState) -> Optional[Dict[str, Any]]:
        """Chama a rota /signal do próprio servidor para obter o sinal."""
        try:
            params = {"symbol": bot.symbol, "tf": bot.timeframe}
            # Certifique-se de que a chamada é para o endereço correto.
            # O Render usa a porta 10000.
            
            response = await self.http_client.get(
                SIGNAL_URL,
                params=params,
                timeout=5 # Tempo limite curto para não travar
            )

            if response.status_code == 200:
                return response.json()
            
            elif response.status_code == 404:
                # 404 é esperado quando não há 20 ticks
                # Não é necessário imprimir log a menos que seja para debug
                return None 
            
            else:
                # --- 🔴 DEBUG CRÍTICO AQUI 🔴 ---
                print(f"[Bot {bot.id[:4]}] ERRO HTTP! Status: {response.status_code}, Resposta: {response.text}")
                return None

        except httpx.ConnectError:
            # --- 🔴 DEBUG CRÍTICO AQUI 🔴 ---
            print(f"[Bot {bot.id[:4]}] ERRO HTTP: Falha ao conectar a {SIGNAL_URL}. Verifique se o servidor está na porta 10000.")
            return None
        
        except Exception as e:
             # --- 🔴 DEBUG CRÍTICO AQUI 🔴 ---
            print(f"[Bot {bot.id[:4]}] ERRO INESPERADO ao obter sinal: {e}")
            return None

    async def run_bot_loop(self, bot: BotState):
        """Loop principal de execução do bot."""
        while bot.is_active:
            try:
                # 1. Obter sinal da API
                signal = await self.get_signal_from_api(bot)

                if signal:
                    print(f"[Bot {bot.id[:4]}] Sinal encontrado: {signal['action']} em {bot.symbol}")
                    
                    # 2. Simulação de execução de ordem (substituir por API real)
                    action = signal['action'].split(' ')[0] # CALL ou PUT
                    
                    print(f"[Bot {bot.id[:4]}] -> EXECUTANDO ORDEM: {action}...")
                    
                    # 3. Atrasar o loop para esperar pelo próximo sinal
                    await asyncio.sleep(60) # Espera 1 minuto após um sinal (simulação)
                else:
                    # Se não houver sinal (404 ou outros erros controlados), verifica novamente em 5 segundos
                    await asyncio.sleep(5) 

            except asyncio.CancelledError:
                # Sai do loop quando a tarefa é cancelada (deactivate_bot)
                print(f"[Bot {bot.id[:4]}] Loop cancelado.")
                break
            except Exception as e:
                # Trata qualquer erro inesperado no loop principal
                print(f"[Bot {bot.id[:4]}] Erro fatal no loop: {e}")
                await asyncio.sleep(10) # Espera antes de tentar novamente


manager = BotsManager()
