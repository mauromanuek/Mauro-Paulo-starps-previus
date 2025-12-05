import asyncio
import websockets
import json


class DerivClient:
    def __init__(self, token: str):
        self.token = token
        self.ws = None
        self.connected = False
        self.authorized = False

    async def start(self):
        """Inicia a conexão completa com a Deriv."""
        try:
            # ENDPOINT CORRETO
            self.ws = await websockets.connect(
                "wss://ws.derivws.com/websockets/v3"
            )

            print("[Deriv] Conexão WebSocket aberta.")
            self.connected = True

            # autorizar token
            await self.authorize()

            if self.authorized:
                print("[Deriv] Token autorizado com sucesso.")
                asyncio.create_task(self.listen())
            else:
                print("[Deriv] Erro: token NÃO autorizado.")
                self.connected = False

        except Exception as e:
            print("[ERRO] Falha ao conectar WebSocket:", e)
            self.connected = False

    async def authorize(self):
        """Envia token e aguarda resposta."""
        try:
            await self.ws.send(json.dumps({"authorize": self.token}))
            resp = await self.ws.recv()
            data = json.loads(resp)

            if data.get("msg_type") == "authorize":
                self.authorized = True
            else:
                print("[Deriv] Falha na autorização:", data)

        except Exception as e:
            print("[ERRO] authorize:", e)

    async def listen(self):
        """Loop de mensagens."""
        print("[Deriv] Iniciando listener…")
        while self.connected:
            try:
                msg = await self.ws.recv()
                data = json.loads(msg)

                print("[TICK]", data)

                # se conexão cair
                if data.get("error"):
                    print("[Deriv] erro:", data["error"])
                    self.connected = False
                    break

            except websockets.ConnectionClosed:
                print("[Deriv] Conexão fechada. Reconectando…")
                self.connected = False
                break

            except Exception as e:
                print("[ERRO] no listener:", e)
                self.connected = False
                break

    async def stop(self):
        """Fecha a conexão."""
        try:
            self.connected = False
            self.authorized = False
            if self.ws:
                await self.ws.close()
        except:
            pass

        print("[Deriv] Cliente parado.")
