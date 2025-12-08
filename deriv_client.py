# deriv_client.py - Versão FINAL E CORRIGIDA: Import e Subscrição de Velas

import asyncio
import json
import websockets # 🟢 CORREÇÃO CRÍTICA: Importar o módulo completo aqui
from typing import Optional, Dict, Any, TYPE_CHECKING
import time

# Importa as variáveis de controlo e a lógica de trading do strategy.py
from strategy import ticks_history, MIN_TICKS_REQUIRED, generate_signal, MAX_TICK_HISTORY

# Apenas para tipagem
if TYPE_CHECKING:
    from bots_manager import BotsManager 

# --- CONFIGURAÇÃO CORRIGIDA (SEU APP ID) ---
DERIV_APP_ID = 114910 
# -------------------------------------------

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
        self.ws: Optional[websockets.WebSocketClientProtocol] = None # Tipo atualizado
        self.is_connected = False
        self.connected = False 
        self.authorized = False 
        self.account_info = {"balance": 0.0, "account_type": "demo"}
        self.symbol = "" 
        self.candles_subscription_id: Optional[str] = None

    # --- FUNÇÕES CORE ---

    async def connect_and_subscribe(self, symbol: str):
        """
        Função de wrapper para iniciar a conexão, autenticar, 
        e iniciar a escuta de velas em sequência (executada em segundo plano).
        """
        await self.connect()
        
        await asyncio.sleep(1) 
        
        if self.is_connected:
            await self.subscribe_candles(symbol)
            await self.run_listener()

    async def connect(self):
        """Estabelece a conexão e autentica."""
        if self.is_connected: return
        try:
            # 🟢 CORREÇÃO AQUI: Usa websockets.connect() que agora está definido 🟢
            self.ws = await websockets.connect(WS_URL)
            self.is_connected = True
            self.connected = True
            print("Conectado ao Deriv WebSocket.")
            await self.ws.send(json.dumps({"authorize": self.token}))
            
            auth_response_str = await self.ws.recv()
            auth_response = json.loads(auth_response_str)

            if auth_response.get("error"):
                print(f"❌ Erro de Autenticação: {auth_response['error']['message']}")
                self.authorized = False
                self.is_connected = False
                return

            self.authorized = True
            print("✅ Autenticação bem-sucedida.")
            await self.get_account_info() 
            
        except Exception as e:
            print(f"❌ Erro ao conectar ao Deriv: {e}")
            self.is_connected = False
            self.connected = False

    async def subscribe_candles(self, symbol: str):
        """Subscreve as velas (OHLC) para um ativo com 1 minuto de granularidade."""
        if not self.is_connected: return
        self.symbol = symbol

        try:
            await self.ws.send(json.dumps({"forget_all": "candles"}))
            
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
                # O Timeout é necessário para enviar Pings
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
                    await self.ws.send(json.dumps({"pong": 1}))
                elif response.get("msg_type") == "balance":
                     if response.get('balance'):
                        self.account_info['balance'] = response['balance'].get('balance', 0.0)

            except asyncio.TimeoutError:
                await self.ws.send(json.dumps({"ping": 1}))
                continue
            except websockets.ConnectionClosedOK: # Adicionado tratamento de fecho limpo
                print("Conexão fechada de forma limpa.")
                self.is_connected = False
                self.connected = False
                break
            except Exception as e:
                print(f"Conexão fechada inesperadamente: {e}")
                self.is_connected = False
                self.connected = False
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
        
        if candle_data.get('is_closed') == 1:
            closed_price = candle_data.get('close')

            if closed_price and self.symbol:
                price_float = float(closed_price)
                
                ticks_history.append(price_float)
                
                if len(ticks_history) > MAX_TICK_HISTORY:
                    del ticks_history[0] 
                
                if len(ticks_history) >= MIN_TICKS_REQUIRED:
                    signal = generate_signal(self.symbol, "1m") 
                    
                    if signal:
                        print(f"=== NOVO SINAL ({signal['tf']}) ===")
                        print(f"Ação: {signal['action']} | Probabilidade: {signal['probability']:.2f} | Razão: {signal['reason']}")
                        print("===================================")
                        await self.bots_manager.process_signal(signal)
                        
    async def get_account_info(self):
        """Busca o saldo e tipo de conta (movido para dentro do connect)."""
        if not self.authorized or not self.is_connected: return

        try:
            # Envia a requisição; a resposta será capturada pelo run_listener
            await self.ws.send(json.dumps({"balance": 1})) 
        except Exception as e:
            print(f"[ERRO] Falha ao buscar informações da conta: {e}")

    async def stop(self):
        """Fecha a conexão."""
        try:
            self.is_connected = False
            self.connected = False
            self.authorized = False
            if self.ws:
                await self.ws.close()
        except:
            pass

        print("[Deriv] Cliente parado.")
