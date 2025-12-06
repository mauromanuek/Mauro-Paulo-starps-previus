# deriv_client.py 

import asyncio
import websockets
import json
from datetime import datetime
# Importa as funções de cálculo da estratégia
from strategy import update_ticks, calculate_indicators, generate_signal 


class DerivClient:
    
    # APP_ID agora é passado no construtor
    def __init__(self, app_id: str):
        self.app_id = app_id
        self.ws = None
        self.connected = False
        self.authorized = False
        self.account_info = {"balance": "N/A", "account_type": "N/A"} 
        self.listener_task = None 
        self.token = None # Não inicializa com o token

    async def connect(self, token: str):
        """
        Conecta e autoriza. Chamado quando o token é submetido.
        """
        self.token = token
        
        if self.ws and self.connected:
            await self.stop()

        try:
            self.ws = await websockets.connect(
                f"wss://ws.derivws.com/websockets/v3?app_id={self.app_id}"
            )
            print("[Deriv] Conexão WebSocket aberta.")
            self.connected = True
            
            await self.authorize()
            
            if self.authorized:
                print("[Deriv] Token autorizado com sucesso. O bot está ONLINE.")
                
                await self.get_account_info()
                
                # Assinaturas essenciais
                await self.subscribe_to_ticks("R_100") # ✅ Mantido o R_100
                await self.subscribe_to_balance()
                
                # Inicia o listener de forma assíncrona
                self.listener_task = asyncio.create_task(self.listen())
            
        except Exception as e:
            print(f"[ERRO DerivClient] Falha na conexão ou autorização: {e}")
            self.connected = False
            self.authorized = False
            raise e # Lança o erro para o main.py


    async def authorize(self):
        """Envia o token para autorização."""
        auth_request = json.dumps({"authorize": self.token})
        await self.ws.send(auth_request)
        
        response = await asyncio.wait_for(self.ws.recv(), timeout=5)
        data = json.loads(response)
        
        if data.get("msg_type") == "authorize" and data["authorize"].get("loginid"):
            self.authorized = True
            self.account_info = {
                "balance": data["authorize"].get("balance"),
                "account_type": data["authorize"].get("account_type"),
            }
        else:
            self.authorized = False
            print(f"[Deriv] Falha na autorização: {data.get('error')}")


    async def subscribe_to_ticks(self, symbol: str):
        """Inicia a subscrição de ticks."""
        print(f"[Deriv] Subscrevendo ticks para: {symbol}")
        await self.ws.send(json.dumps({"ticks": symbol, "subscribe": 1}))

    async def subscribe_to_balance(self):
        """Inicia a subscrição do saldo."""
        print("[Deriv] Subscrevendo saldo.")
        await self.ws.send(json.dumps({"balance": 1, "subscribe": 1}))

    async def get_account_info(self):
        """Obtém as informações da conta (após autorização)."""
        # A informação da conta já é obtida na autorização.
        pass

    def calculate_signal(self, symbol: str, tf: int):
        """
        Calcula o sinal usando a estratégia. 
        Chamado pela rota /signal no main.py.
        """
        indicators = calculate_indicators()
        
        if not indicators:
            return {"action": "AGUARDANDO", "indicators": {}}

        signal_data = generate_signal(indicators)
        
        if signal_data is None:
            return {"action": "AGUARDANDO", "indicators": indicators}
            
        signal_data["indicators"] = indicators
        return signal_data
        
        
    async def listen(self):
        """Loop de escuta para receber dados do WebSocket."""
        while self.connected:
            try:
                response = await asyncio.wait_for(self.ws.recv(), timeout=25) 
                data = json.loads(response)

                if data.get("error"):
                    print(f"[Deriv ERRO] {data['error'].get('message')}")
                    continue 
                
                if data.get("msg_type") == "tick":
                    tick = data["tick"]
                    price = float(tick["quote"])
                    update_ticks(price) 
                    
                if data.get("msg_type") == "balance" and data.get('balance'):
                    self.account_info['balance'] = data['balance'].get('balance')

            except websockets.ConnectionClosed as e:
                print(f"[Deriv] Conexão fechada. Motivo: {e}.")
                self.connected = False
                self.authorized = False
                break
            except asyncio.TimeoutError:
                if self.connected:
                    await self.ws.send(json.dumps({"ping": 1}))
                continue
            except Exception as e:
                print(f"[ERRO GERAL] no listener: {e}")
                continue

    async def stop(self):
        """Fecha a conexão."""
        # Lógica para parar a tarefa de listen
        try:
            if self.listener_task:
                self.listener_task.cancel()
            self.connected = False
            self.authorized = False
            if self.ws:
                await self.ws.close()
        except Exception as e:
            print(f"[ERRO ao parar DerivClient]: {e}")
        print("[Deriv] Cliente parado.")
                
