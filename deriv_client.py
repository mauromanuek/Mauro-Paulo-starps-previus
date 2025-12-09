# deriv_client.py - Versão FINAL E ESTÁVEL: Baseada em Velas (OHLC)

import asyncio
import json
import websockets 
from typing import Optional, Dict, Any, TYPE_CHECKING
import time

# --- IMPORTS OBRIGATÓRIOS ---
from strategy import ticks_history, MIN_TICKS_REQUIRED, generate_signal, MAX_TICK_HISTORY

if TYPE_CHECKING:
    from bots_manager import BotsManager 

# --- CONFIGURAÇÃO (SEU APP ID) ---
DERIV_APP_ID = 114910 
# ---

WS_URL = f"wss://ws.binaryws.com/websockets/v3?app_id={DERIV_APP_ID}" 
CANDLE_GRANULARITY = 60 # 1 Minuto

class DerivClient:
    
    def __init__(self, token: str, bots_manager: 'BotsManager'): 
        self.token = token
        self.bots_manager = bots_manager
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.connected = False 
        self.authorized = False 
        self.history_loaded = False  # FLAG CRÍTICA
        self.account_info = {"balance": 0.0, "account_type": "demo"}
        self.symbol = "" 
        self.candles_subscription_id: Optional[str] = None
        self.last_processed_candle_time = 0 

    # --- FUNÇÕES CORE ---

    async def connect_and_subscribe(self, symbol: str):
        await self.connect()
        await asyncio.sleep(1) 
        
        if self.authorized: 
            await self.subscribe_candles(symbol) # 👈 CRÍTICO: CHAMA AS VELAS
            
            timeout = 20
            start_time = time.time()
            print("[Deriv] Aguardando o histórico inicial de velas...")
            
            listener_task = asyncio.create_task(self.run_listener())
            
            while not self.history_loaded and time.time() - start_time < timeout:
                await asyncio.sleep(0.5)

            if self.history_loaded:
                print("✅ Histórico carregado. O bot está PRONTO.")
            else:
                print(f"❌ Falha no carregamento do histórico inicial (Timeout de {timeout}s).")
                listener_task.cancel()
                await self.stop()
        else:
            await self.stop()

    async def connect(self):
        if self.is_connected: return
        try:
            self.ws = await websockets.connect(WS_URL)
            self.is_connected = True
            self.connected = True
            print("[Deriv] Conectado ao Deriv WebSocket.")
            await self.ws.send(json.dumps({"authorize": self.token}))
            
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
            print(f"❌ Erro de Conexão: O WebSocket foi fechado. Código: {e.code}. Verifique o token e a rede.")
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
                "style": "candles", # 👈 CRÍTICO: Garante que está a pedir velas
                "granularity": CANDLE_GRANULARITY 
            }))
            print(f"Subscrito aos dados de Velas de 1 Minuto para {symbol}")
        except Exception as e:
            print(f"❌ Erro ao subscrever velas: {e}")

    async def run_listener(self):
        while self.is_connected and self.ws:
            try:
                response_str = await asyncio.wait_for(self.ws.recv(), timeout=30) 
                response = json.loads(response_str)
                
                # Processa a nova vela fechada
                if response.get('ohlc'):
                    await self.handle_candle_update(response)
                # Processa o histórico inicial (o grande pacote)
                elif response.get('candles'):
                    self.handle_history_response(response) 
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
        """Define a flag CRÍTICA como True."""
        global ticks_history
        history = response.get('candles', [])
        
        if history:
            ticks_history.clear()
            ticks_history.extend([float(c.get('close')) for c in history])
            
            if history:
                 self.last_processed_candle_time = history[-1].get('open_time', 0)
            
            self.history_loaded = True # 👈 A SOLUÇÃO: A flag só é True aqui
            print(f"✅ Histórico de velas de 1m carregado: {len(ticks_history)} preços de fecho.")
    
    # ... (Resto das funções omitido por brevidade)
    async def handle_candle_update(self, response: Dict[str, Any]):
        global ticks_history
        candle_data = response.get('ohlc', {})
        if candle_data.get('is_closed') == 1 and self.history_loaded: 
            candle_time = candle_data.get('open_time', 0) 
            if candle_time <= self.last_processed_candle_time:
                 return 
            closed_price = candle_data.get('close')
            if closed_price and self.symbol:
                price_float = float(closed_price)
                ticks_history.append(price_float)
                if len(ticks_history) > MAX_TICK_HISTORY:
                    del ticks_history[0] 
                self.last_processed_candle_time = candle_time
                if len(ticks_history) >= MIN_TICKS_REQUIRED:
                    signal = generate_signal(self.symbol, "1m") 
                    if signal and signal['action'] != 'NEUTRO': 
                        print(f"=== NOVO SINAL ({signal['tf']}) ===")
                        print(f"Ação: {signal['action']} | Prob: {signal['probability']:.2f} | Razão: {signal['reason']}")
                        asyncio.create_task(self.bots_manager.process_signal(signal)) # Use create_task para evitar bloqueio

    async def get_account_info(self):
        if not self.authorized or not self.is_connected: return
        try:
            await self.ws.send(json.dumps({"balance": 1})) 
        except Exception as e:
            print(f"[ERRO] Falha ao buscar informações da conta: {e}")

    async def stop(self):
        try:
            self.is_connected = False
            self.connected = False
            self.authorized = False
            self.history_loaded = False
            if self.ws:
                await self.ws.close()
        except:
            pass
        print("[Deriv] Cliente parado.")
