# deriv_client.py
import asyncio
import json
import websockets
import time
from collections import deque
from typing import Optional, Callable, Deque, Dict, Any

DERIV_APP_ID = 114910
WS_URL = f"wss://ws.derivws.com/websockets/v3?app_id={DERIV_APP_ID}"

DEFAULT_GRANULARITY = 60  # seconds
HISTORY_CANDLES = 500     # quantas velas manter por ativo


class Candle:
    def __init__(self, open_p: float, high: float, low: float, close: float, start_ts: int):
        self.open = float(open_p)
        self.high = float(high)
        self.low = float(low)
        self.close = float(close)
        self.start_ts = int(start_ts)

    def to_dict(self):
        return {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "start_ts": self.start_ts
        }


class DerivClient:
    def __init__(self, app_id: Optional[int] = None):
        self.app_id = app_id or DERIV_APP_ID
        self.ws_url = f"wss://ws.derivws.com/websockets/v3?app_id={self.app_id}"
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.authorized = False
        self.token: Optional[str] = None

        # callbacks set by main.py
        self.on_tick: Optional[Callable[[dict], None]] = None
        self.on_candle: Optional[Callable[[str, int, Dict[str, Any]], None]] = None
        self.on_history_ready: Optional[Callable[[str, int], None]] = None

        # stores
        # candles_store[symbol][gran] -> deque[Candle]
        self.candles_store: Dict[str, Dict[int, Deque[Candle]]] = {}
        # builder state for symbol->gran
        self.build_candle: Dict[str, Dict[int, Dict[str, Any]]] = {}
        # last tick
        self.last_tick: Dict[str, float] = {}

        self._listener_task: Optional[asyncio.Task] = None

    # ------------- connection & auth -------------
    async def connect(self, token: str):
        if self.is_connected:
            return
        self.token = token
        try:
            self.ws = await websockets.connect(self.ws_url)
            self.is_connected = True
            await self._authorize()
            if self.authorized:
                self._listener_task = asyncio.create_task(self._listener_loop())
                print("[DerivClient] Conectado, autorizado e listener iniciado.")
            else:
                print("[DerivClient] Conexão falhou por problemas de autorização.")
                await self.ws.close()
                self.is_connected = False
        except Exception as e:
            print("[DerivClient] Erro ao conectar:", e)
            self.is_connected = False

    async def _authorize(self):
        """Tenta autorizar a sessão com o token fornecido."""
        self.authorized = False
        if not self.ws or not self.token:
            print("[DerivClient] Erro: WS ou token ausente para autorização.")
            return

        await self.ws.send(json.dumps({"authorize": self.token}))
        print("[DerivClient] Enviando requisição de autorização...")

        try:
            # Espera pela resposta de autorização por até 10 segundos
            resp = await asyncio.wait_for(self.ws.recv(), timeout=10)
            j = json.loads(resp)

            if j.get("msg_type") == "authorize" and j.get("authorize"):
                # Autorização bem-sucedida
                self.authorized = True
                client_id = j['authorize'].get('client_id')
                print(f"[DerivClient] Autorizado com sucesso. Client ID: {client_id}")
            
            elif j.get("error"):
                # Captura erros de token inválido, permissões, etc.
                error_code = j['error']['code']
                error_msg = j['error']['message']
                print(f"[DerivClient] ERRO de autorização: [{error_code}] {error_msg}")
            
            else:
                # Caso a resposta seja inesperada
                print("[DerivClient] Resposta authorize inesperada:", j)

        except asyncio.TimeoutError:
            print("[DerivClient] Timeout: Não recebeu resposta de autorização em 10s.")
        except Exception as e:
            print(f"[DerivClient] authorize erro geral: {e}")

    # ------------- subscriptions -------------
    async def subscribe_ticks(self, symbol: str):
        if not self.is_connected or not self.authorized or not self.ws:
            raise RuntimeError("Não conectado ou não autorizado")
        await self.ws.send(json.dumps({"ticks": symbol, "subscribe": 1}))
        print(f"[DerivClient] Subscrito ticks: {symbol}")

    async def subscribe_candles_history(self, symbol: str, granularity: int = DEFAULT_GRANULARITY, count: int = 150):
        if not self.is_connected or not self.authorized or not self.ws:
            raise RuntimeError("Não conectado ou não autorizado")
        body = {
            "ticks_history": symbol,
            "style": "candles",
            "granularity": granularity,
            "count": count,
            "end": "latest",
            "subscribe": 1
        }
        await self.ws.send(json.dumps(body))
        print(f"[DerivClient] Solicitado histórico de candles {symbol} gran={granularity} count={count}")

    # ------------- listener -------------
    async def _listener_loop(self):
        assert self.ws
        while self.is_connected:
            try:
                raw = await self.ws.recv()
                j = json.loads(raw)
                
                if j.get("tick"):
                    await self._process_tick(j["tick"])
                elif j.get("ohlc"):
                    await self._process_official_candle(j["ohlc"])
                elif j.get("candles"):
                    await self._process_history_candles(j)
                elif j.get("msg_type") == "balance":
                    # Opcional: propagar saldo ou outras mensagens
                    pass
                elif j.get("error"):
                    # Captura erros assíncronos (e.g., erro de subscrição)
                    print(f"[DerivClient] ERRO assíncrono: {j['error'].get('message')}")

            except websockets.ConnectionClosed:
                print("[DerivClient] Websocket fechado pelo servidor.")
                self.is_connected = False
                break
            except Exception as e:
                print("[DerivClient] Erro no listener:", e)
                await asyncio.sleep(0.5)
                continue

    # ------------- ticks -> build candles -------------
    async def _process_tick(self, tick: dict):
        symbol = tick.get("symbol")
        if symbol is None:
            return
        quote = float(tick.get("quote"))
        epoch = int(tick.get("epoch"))

        self.last_tick[symbol] = quote
        if self.on_tick:
            try:
                self.on_tick({"symbol": symbol, "quote": quote, "epoch": epoch})
            except Exception:
                pass

        if symbol not in self.build_candle:
            return

        for gran, state in list(self.build_candle[symbol].items()):
            start_ts = (epoch // gran) * gran
            if state["start_ts"] is None:
                state["start_ts"] = start_ts
                state["open"] = quote
                state["high"] = quote
                state["low"] = quote
                state["close"] = quote
            elif start_ts != state["start_ts"]:
                # commit closed candle
                closed = Candle(state["open"], state["high"], state["low"], state["close"], state["start_ts"])
                await self._commit_candle(symbol, gran, closed)
                # start new
                state["start_ts"] = start_ts
                state["open"] = quote
                state["high"] = quote
                state["low"] = quote
                state["close"] = quote
            else:
                # update current
                state["close"] = quote
                if quote > state["high"]:
                    state["high"] = quote
                if quote < state["low"]:
                    state["low"] = quote

    async def _commit_candle(self, symbol: str, gran: int, candle: Candle):
        store = self.candles_store.setdefault(symbol, {})
        dq = store.setdefault(gran, deque(maxlen=HISTORY_CANDLES))
        if dq and dq[-1].start_ts >= candle.start_ts:
            return
        dq.append(candle)
        if self.on_candle:
            try:
                self.on_candle(symbol, gran, candle.to_dict())
            except Exception:
                pass

    # ------------- official candles & history -------------
    async def _process_official_candle(self, ohlc: dict):
        symbol = ohlc.get("symbol")
        gran = int(ohlc.get("granularity", DEFAULT_GRANULARITY))
        start_ts = int(ohlc.get("open_time"))
        close = float(ohlc.get("close"))
        high = float(ohlc.get("high"))
        low = float(ohlc.get("low"))
        open_p = float(ohlc.get("open"))
        candle = Candle(open_p, high, low, close, start_ts)
        await self._commit_candle(symbol, gran, candle)

    async def _process_history_candles(self, response: dict):
        symbol = response.get("symbol") or response.get("echo_req", {}).get("ticks_history")
        gran = int(response.get("echo_req", {}).get("granularity", DEFAULT_GRANULARITY))
        data = response.get("candles", [])
        if not data:
            return
        store = self.candles_store.setdefault(symbol, {})
        dq = store.setdefault(gran, deque(maxlen=HISTORY_CANDLES))
        dq.clear()
        for c in data:
            try:
                open_p = float(c.get("open"))
                high = float(c.get("high"))
                low = float(c.get("low"))
                close = float(c.get("close"))
                start_ts = int(c.get("open_time"))
                dq.append(Candle(open_p, high, low, close, start_ts))
            except Exception:
                continue
        if self.on_history_ready:
            try:
                self.on_history_ready(symbol, gran)
            except Exception:
                pass

    # ------------- helpers -------------
    def get_latest_candles(self, symbol: str, gran: int, count: int = 200):
        store = self.candles_store.get(symbol, {})
        dq = store.get(gran, deque())
        return [c.to_dict() for c in list(dq)[-count:]]

    def get_last_tick(self, symbol: str):
        return {"symbol": symbol, "quote": self.last_tick.get(symbol)}

    def ensure_candle_builder(self, symbol: str, gran: int = DEFAULT_GRANULARITY):
        self.build_candle.setdefault(symbol, {})
        self.build_candle[symbol].setdefault(gran, {
            "start_ts": None,
            "open": None,
            "high": None,
            "low": None,
            "close": None
        })
        self.candles_store.setdefault(symbol, {})
        self.candles_store[symbol].setdefault(gran, deque(maxlen=HISTORY_CANDLES))

    # ------------- shutdown -------------
    async def stop(self):
        self.is_connected = False
        if self._listener_task:
            self._listener_task.cancel()
        try:
            if self.ws:
                await self.ws.close()
        except:
            pass
        print("[DerivClient] Stopped.")
