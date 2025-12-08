# deriv_client.py - Versão Atualizada e Final: Subscrição de Velas (Estabilidade)

import asyncio
import json
from websockets import connect
from typing import Optional, Dict, Any, TYPE_CHECKING
import time

# Importa as variáveis de controlo e a lógica de trading do strategy.py
from strategy import ticks_history, MIN_TICKS_REQUIRED, generate_signal, MAX_TICK_HISTORY

# Apenas para tipagem
if TYPE_CHECKING:
    from bots_manager import BotsManager 

# --- CONFIGURAÇÃO CORRIGIDA ---
# 🚨 SEU APP ID INSERIDO AQUI 🚨
DERIV_APP_ID = 114910 
# ------------------------------

WS_URL = f"wss://ws.binaryws.com/websockets/v3?app_id={DERIV_APP_ID}"
CANDLE_GRANULARITY = 60 # 60 segundos = 1 Minuto (para sinais estáveis)

class DerivClient:
    """
    Gerencia a conexão WebSocket com a Deriv, autentica, gere o stream de dados 
    de velas de 1 minuto e envia sinais estáveis para o BotsManager.
    """
    def __init__(self, token: str, bots_manager: 'BotsManager'):
        self.token = token
        self.bots_manager = bots_manager
        self.ws: Optional[connect] = None
        self.is_connected = False
        self.symbol = "" 
        self.candles_subscription_id: Optional[str] = None # Para gerir a subscrição

    async def connect(self):
        """Estabelece a conexão e autentica."""
        if self.is_connected: return
        try:
            self.ws = await connect(WS_URL)
            self.is_connected = True
            print("Conectado ao Deriv WebSocket.")
            await self.ws.send(json.dumps({"authorize": self.token}))
            auth_response = json.loads(await self.ws.recv())
            if auth_response.get("error"):
                print(f"❌ Erro de Autenticação: {auth_response['error']['message']}")
                self.is_connected = False
                return
            print("✅ Autenticação bem-sucedida.")
        except Exception as e:
            print(f"❌ Erro ao conectar ao Deriv: {e}")
            self.is_connected = False


    async def subscribe_candles(self, symbol: str):
        """Subscreve as velas (OHLC) para um ativo com 1 minuto de granularidade."""
        if not self.is_connected: return
        self.symbol = symbol

        try:
            # Pede o histórico e subscreve as novas velas (timeframe de 1 minuto)
            await self.ws.send(json.dumps({
                "forget_all": "candles" # Limpa quaisquer subscrições de velas anteriores
            }))
            
            await self.ws.send(json.dumps({
                "ticks_history": symbol,
                "end": "latest",
                "start": 1,
                "count": MAX_TICK_HISTORY,
                "subscribe": 1,
                "style": "candles",
                "granularity": CANDLE_GRANULARITY 
            }))
            print(f"Subscrito aos dados de Velas de 1 Minuto para {symbol}")
        except Exception as e:
            print(f"❌ Erro ao subscrever velas: {e}")

    async def run_listener(self):
        """Loop principal para escutar mensagens do WebSocket."""
        while self.is_connected and self.ws:
            try:
                # Timeout para poder enviar pings
                response_str = await asyncio.wait_for(self.ws.recv(), timeout=30) 
                response = json.loads(response_str)
                
                if response.get('error'):
                    print(f"❌ Erro da API: {response['error']['message']}")
                elif response.get('ohlc'):
                    await self.handle_candle_update(response)
                elif response.get('candles'):
                    self.handle_history_response(response)
                elif response.get('msg_type') == 'candles':
                    self.candles_subscription_id = response.get('subscription', {}).get('id')
                elif response.get('msg_type') == 'ping':
                    # Responde ao ping da API (Manter conexão ativa)
                    await self.ws.send(json.dumps({"pong": 1}))

            except asyncio.TimeoutError:
                # Se o timeout for atingido, envia um ping para o servidor Deriv
                await self.ws.send(json.dumps({"ping": 1}))
                continue
            except Exception as e:
                print(f"Conexão fechada inesperadamente: {e}")
                self.is_connected = False
                break
    
    def handle_history_response(self, response: Dict[str, Any]):
        """Processa o histórico inicial de velas."""
        global ticks_history
        history = response.get('candles', [])
        
        if history:
            ticks_history.clear()
            ticks_history.extend([float(c.get('close')) for c in history])
            
            print(f"✅ Histórico de velas de 1m carregado: {len(ticks_history)} preços de fecho.")
            
    
    async def handle_candle_update(self, response: Dict[str, Any]):
        """
        Processa uma nova vela (quando o 'is_closed' é 1) e chama a análise.
        """
        global ticks_history

        candle_data = response.get('ohlc', {})
        
        # O preço de fecho (close) só é confiável quando a vela está fechada (is_closed: 1)
        if candle_data.get('is_closed') == 1:
            closed_price = candle_data.get('close')

            if closed_price and self.symbol:
                price_float = float(closed_price)
                
                # 1. Adicionar o novo preço de fecho
                ticks_history.append(price_float)
                
                # 2. Gerir o tamanho da lista (Limpeza)
                if len(ticks_history) > MAX_TICK_HISTORY:
                    del ticks_history[0] 
                
                # 3. Análise e Decisão da Estratégia
                if len(ticks_history) >= MIN_TICKS_REQUIRED:
                    signal = generate_signal(self.symbol, "1m") 
                    
                    if signal:
                        print(f"=== NOVO SINAL ({signal['tf']}) ===")
                        print(f"Ação: {signal['action']} | Probabilidade: {signal['probability']:.2f} | Razão: {signal['reason']}")
                        print("===================================")
                        await self.bots_manager.process_signal(signal)


# ----------------------------------------------------------------------
# FUNÇÃO DE EXECUÇÃO PRINCIPAL
# ----------------------------------------------------------------------

# Assumimos que BotsManager existe
async def main():
    
    # 🚨 SUBSTITUA ESTES VALORES 🚨
    YOUR_API_TOKEN = "SEU_TOKEN_AQUI"
    TRADING_SYMBOL = "R_100" # Exemplo: Volatility 100 Index
    
    if YOUR_API_TOKEN == "SEU_TOKEN_AQUI":
        print("🚨 Por favor, insira o seu token da Deriv para continuar. 🚨")
        return

    try:
        from bots_manager import BotsManager
    except ImportError:
        print("🚨 Erro: O arquivo bots_manager.py não foi encontrado. 🚨")
        return

    # Um BotsManager simples para fins de demonstração
    class SimpleBotsManager:
        async def process_signal(self, signal):
            print(f"🤖 BOT_MANAGER: Recebido sinal de {signal['action']} ({signal['tf']})")

    bots_manager_instance = SimpleBotsManager() 
    client = DerivClient(token=YOUR_API_TOKEN, bots_manager=bots_manager_instance)

    await client.connect()
    
    if client.is_connected:
        await client.subscribe_candles(TRADING_SYMBOL)
        await client.run_listener()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCliente Deriv encerrado pelo utilizador.")
