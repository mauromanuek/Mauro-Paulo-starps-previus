import asyncio
import websockets
import json


class DerivClient:
    def __init__(self, token: str):
        self.token = token
        self.ws = None
        self.connected = False
        self.listening = False

    async def start(self):
        """Inicia a conexão com a Deriv."""
        try:
            self.ws = await websockets.connect("wss://ws.binaryws.com/websockets/v3")
            self.connected = True

            await self.authorize()

            # após autorizar, começa a receber ticks
            asyncio.create_task(self.listen())

        except Exception as e:
            print("Erro ao conectar:", e)

    async def authorize(self):
        """Autoriza o token."""
        try:
            await self.ws.send(json.dumps({"authorize": self.token}))
        except:
            pass

    async def listen(self):
        """Lê mensagens da Deriv em loop."""
        self.listening = True
        while self.connected:
            try:
                msg = await self.ws.recv()
                data = json.loads(msg)
                print("Tick recebido:", data)

            except websockets.ConnectionClosed:
                print("Conexão perdida. Tentando reconectar...")
                self.connected = False
                break

            except Exception as e:
                print("Erro ao ler mensagem:", e)
                break

    async def stop(self):
        """Desliga o cliente atual."""
        self.connected = False
        self.listening = False

        try:
            if self.ws:
                await self.ws.close()
        except:
            pass
