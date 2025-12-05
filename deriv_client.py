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
        
        # O SEU APP ID FOI INSERIDO AQUI: 114910
        APP_ID = "114910" 
        
        try:
            # ENDPOINT CORRETO (AGORA COM O APP ID)
            self.ws = await websockets.connect(
                f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}"
            )

            print("[Deriv] Conexão WebSocket aberta.")
            self.connected = True

            # autorizar token
            await self.authorize()

            if self.authorized:
                print("[Deriv] Token autorizado com sucesso. O bot está ONLINE.")
                asyncio.create_task(self.listen())
            else:
                print("[Deriv] Erro: token NÃO autorizado. Verifique se o token está correto e ativo.")
                self.connected = False

        except Exception as e:
            print("[ERRO] Falha ao conectar WebSocket (URL/Rede):", e)
            self.connected = False

    async def authorize(self):
        """Envia token e aguarda resposta."""
        try:
            await self.ws.send(json.dumps({"authorize": self.token}))
            resp = await self.ws.recv()
            data = json.loads(resp)
            
            # Verificação de sucesso na autorização
            if data.get("msg_type") == "authorize" and not data.get("error"):
                self.authorized = True
            elif data.get("error"):
                print("[Deriv] Falha na autorização:", data["error"])
            else:
                print("[Deriv] Resposta de autorização inesperada:", data)

        except Exception as e:
            print("[ERRO] authorize:", e)

    async def listen(self):
        """Loop de mensagens."""
        print("[Deriv] Iniciando listener de ticks…")
        while self.connected:
            try:
                msg = await self.ws.recv()
                data = json.loads(msg)

                # Se a Deriv enviar uma mensagem de erro em um tick, logamos e paramos
                if data.get("error"):
                    print("[ERRO FATAL DERIV]:", data["error"])
                    self.connected = False
                    break

                # Caso contrário, processamos os dados (ticks, propostas, etc.)
                print("[TICK]", data)


            except websockets.ConnectionClosed as e:
                print(f"[Deriv] Conexão fechada. Motivo: {e}. Desligando cliente.")
                self.connected = False
                break

            except Exception as e:
                print(f"[ERRO GERAL] no listener: {e}")
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
    
