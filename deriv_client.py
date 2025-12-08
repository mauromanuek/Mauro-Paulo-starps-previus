# deriv_client.py - Versão FINAL E CORRIGIDA: Import, Velas de 1m, e Tratamento de Conexão

import asyncio
import json
import websockets # 🟢 CORREÇÃO: Importação do módulo completo
from typing import Optional, Dict, Any, TYPE_CHECKING
import time

# Importa as variáveis de controlo e a lógica de trading do strategy.py
from strategy import ticks_history, MIN_TICKS_REQUIRED, generate_signal, MAX_TICK_HISTORY

# Apenas para tipagem
if TYPE_CHECKING:
    from bots_manager import BotsManager 

# --- CONFIGURAÇÃO (SEU APP ID) ---
DERIV_APP_ID = 114910 
# ---

# URL padrão para a API WebSocket
WS_URL = f"wss://ws.binaryws.com/websockets/v3?app_id={DERIV_APP_ID}" 
CANDLE_GRANULARITY = 60 # 1 Minuto

class DerivClient:
    """
    Gerencia a conexão WebSocket com a Deriv, autentica, gere o stream de dados 
    de velas de 1 minuto e envia sinais estáveis para o BotsManager.
    """
    def __init__(self, token: str, bots_manager: 'BotsManager'): 
        self.token = token
        self.bots_manager = bots_manager
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.connected = False 
        self.authorized = False 
        self.account_info = {"balance": 0.0, "account_type": "demo"}
        self.symbol = "" 
        self.candles_subscription_id: Optional[str] = None

    # --- FUNÇÕES CORE ---

    async def connect_and_subscribe(self, symbol: str):
        """Inicia a conexão, autenticação e subscrição em sequência."""
        await self.connect()
        await asyncio.sleep(1) 
        
        if self.authorized: 
            await self.subscribe_candles(symbol)
            await self.run_listener()
        else:
            await self.stop()


    async def connect(self):
        """Estabelece a conexão e autentica, tratando falhas imediatas."""
        if self.is_connected: return
        try:
            # Estabelece a conexão
            self.ws = await websockets.connect(WS_URL)
            self.is_connected = True
            self.connected = True
            print("[Deriv] Conectado ao Deriv WebSocket.")
            await self.ws.send(json.dumps({"authorize": self.token}))
            
            # Espera 5 segundos pela resposta de autorização
            auth_response_str = await asyncio.wait_for(self.ws.recv(), timeout=5)
            auth_response = json.loads(auth_response_str)

            if auth_response.get("error"):
                print(f"❌ Erro de Autenticação: {auth_response['error']['message']}")
                self.authorized = False
                self.is_connected = False
                return

            self.authorized = True
            print("✅ Autenticação bem-sucedida.")
            await self.get_account_info() 
            
        except websockets.ConnectionClosed as e:
            # 🟢 TRATAMENTO DO ERRO "sent 1000 (OK)": O WebSocket fechou antes da autenticação.
            print(f"❌ Erro de Conexão: O WebSocket foi fechado imediatamente. Código: {e.code}. Verifique o token e a rede.")
            self.is_connected = False
            self.connected = False
            
        except asyncio.TimeoutError:
            print("❌ Erro de Conexão: Timeout ao esperar pela resposta de autorização (5s).")
            self.is_connected = False
            self.connected = False

        except Exception as e:
            print(f"❌ Erro geral ao conectar ao Deriv: {e}")
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
            except websockets.ConnectionClosedOK:
                print("[Deriv] Conexão fechada de forma limpa.")
                self.is_connected = False
                self.connected = False
                break
            except Exception as e:
                print(f"[Deriv] Conexão fechada inesperadamente no listener: {e}")
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
        """Processa uma nova vela fechada e gera o sinal."""
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
        """Busca o saldo e tipo de conta."""
        if not self.authorized or not self.is_connected: return
        try:
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
