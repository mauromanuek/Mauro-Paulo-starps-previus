import asyncio
import websockets
import json
from typing import Optional, Callable


class DerivClient:
    def __init__(self, token: Optional[str] = None, app_id: Optional[int] = None):
        self.token = token
        self.app_id = app_id
        self.ws = None
        self.connected = False
        self.balance = 0
        self.account_type = None
        self.on_tick: Optional[Callable[[dict], None]] = None
        self.on_authorized: Optional[Callable[[dict], None]] = None
        self.tick_listener_task = None

    # -------------------------------------------------------
    # URL COM APP_ID DINÂMICO
    # -------------------------------------------------------
    def _ws_url(self):
        aid = self.app_id if self.app_id else 1089
        return f"wss://ws.derivws.com/websockets/v3?app_id={aid}"

    # -------------------------------------------------------
    # INICIAR CONEXÃO
    # -------------------------------------------------------
    async def connect(self):
        try:
            print("[Deriv] Abrindo conexão WebSocket...")
            self.ws = await websockets.connect(self._ws_url())
            self.connected = True
            print("[Deriv] Conexão WebSocket aberta.")

            await self._authorize()

            # Começar listener de ticks
            if not self.tick_listener_task:
                self.tick_listener_task = asyncio.create_task(self._tick_listener())

        except Exception as e:
            print("[Deriv] Erro ao conectar:", e)
            self.connected = False

    # -------------------------------------------------------
    # AUTORIZAÇÃO
    # -------------------------------------------------------
    async def _authorize(self):
        if not self.token:
            print("[Deriv] ERRO: Token não definido.")
            return

        await self.ws.send(json.dumps({"authorize": self.token}))
        print("[Deriv] Token enviado para autorização.")

    # -------------------------------------------------------
    # LISTENER DE TICKS
    # -------------------------------------------------------
    async def _tick_listener(self):
        print("[Deriv] Iniciando listener de mensagens…")
        while self.connected:
            try:
                msg = await self.ws.recv()
                data = json.loads(msg)

                # Autorizado
                if data.get("msg_type") == "authorize":
                    self.balance = data["authorize"]["balance"]
                    self.account_type = data["authorize"]["account_type"]
                    print(f"[Deriv] Token autorizado com sucesso. Saldo: {self.balance} ({self.account_type})")

                # Tick recebido
                if data.get("msg_type") == "tick":
                    if self.on_tick:
                        self.on_tick(data["tick"])

            except websockets.ConnectionClosed:
                print("[Deriv] Conexão perdida. Tentando reconectar...")
                self.connected = False
                break
            except Exception as e:
                print("[Deriv] Erro ao ler mensagem:", e)
                break

    # -------------------------------------------------------
    # SUBSCRIÇÃO DE TICKS
    # -------------------------------------------------------
    async def subscribe_symbol(self, symbol: str):
        if not self.connected:
            print("[Deriv] ERRO: cliente não conectado.")
            return

        await self.ws.send(json.dumps({
            "ticks": symbol,
            "subscribe": 1
        }))
        print(f"[Deriv] Subscrição enviada para {symbol}.")

    # -------------------------------------------------------
    # ENCERRAR CONEXÃO
    # -------------------------------------------------------
    async def disconnect(self):
        self.connected = False
        try:
            if self.ws:
                await self.ws.close()
                print("[Deriv] WebSocket fechado.")
        except:
            pass
