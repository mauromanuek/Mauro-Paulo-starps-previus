# deriv_client.py 

import asyncio
import websockets
import json
from datetime import datetime
from strategy import update_ticks


class DerivClient:
    
    # SEU APP ID INSERIDO AQUI
    APP_ID = "114910" 

    def __init__(self, token: str):
        self.token = token
        self.ws = None
        self.connected = False
        self.authorized = False
        self.account_info = {"balance": 0.0, "account_type": "demo"} 

    async def start(self):
        """Inicia a conexão completa com a Deriv."""
        try:
            self.ws = await websockets.connect(
                f"wss://ws.derivws.com/websockets/v3?app_id={self.APP_ID}"
            )
            print("[Deriv] Conexão WebSocket aberta.")
            self.connected = True
            await self.authorize()

            if self.authorized:
                print("[Deriv] Token autorizado com sucesso. O bot está ONLINE.")
                
                await self.get_account_info() 
                print("[Deriv] DEBUG: Informações da conta processadas.") 
                
                # --- 🟢 CORREÇÃO CRÍTICA AQUI: MUDANÇA DE V100 PARA R_100 🟢 ---
                await self.subscribe_to_ticks("R_100") 
                
                print("[Deriv] DEBUG: Tentando iniciar o listener de ticks...")
                asyncio.create_task(self.listen())
                print("[Deriv] DEBUG: Tarefa de listener iniciada. Aguardando ticks...")

            else:
                print("[Deriv] Erro: token NÃO autorizado. Verifique se o token está correto e ativo.")
                self.connected = False
        except Exception as e:
            print("[ERRO] Falha ao conectar WebSocket (URL/Rede):", e)
            self.connected = False
            
    async def subscribe_to_ticks(self, symbol: str):
        """Subscreve explicitamente aos ticks de um ativo."""
        if not self.authorized or not self.connected: return
        try:
            # Enviando a mensagem de subscrição para o ativo corrigido
            await self.ws.send(json.dumps({"ticks": symbol, "subscribe": 1}))
            print(f"[Deriv] Subscrição enviada para {symbol}.")
        except Exception as e:
            print(f"[ERRO] Falha ao subscrever ticks: {e}")


    async def authorize(self):
        """Envia token e aguarda resposta."""
        try:
            await self.ws.send(json.dumps({"authorize": self.token}))
            resp = await self.ws.recv()
            data = json.loads(resp)
            if data.get("msg_type") == "authorize" and not data.get("error"):
                self.authorized = True
            elif data.get("error"):
                print("[Deriv] Falha na autorização:", data["error"])
        except Exception as e:
            print("[ERRO] authorize:", e)

    async def get_account_info(self):
        """Busca o saldo e tipo de conta."""
        if not self.authorized or not self.connected: return

        try:
            await self.ws.send(json.dumps({"balance": 1}))
            resp_balance = await self.ws.recv()
            balance_data = json.loads(resp_balance)

            if balance_data.get('balance'):
                balance_info = balance_data['balance']
                self.account_info['balance'] = balance_info.get('balance', 0.0)
                
                login_id = balance_info.get('loginid', '')
                self.account_info['account_type'] = "demo" if "VRTC" in login_id else "real"
                
                print(f"[Deriv] Saldo Atualizado: {self.account_info['balance']} ({self.account_info['account_type']})")

        except Exception as e:
            print(f"[ERRO] Falha ao buscar informações da conta: {e}")

    async def listen(self):
        """Loop de mensagens e envio de ticks para a estratégia."""
        print("[Deriv] Iniciando listener de ticks…")
        while self.connected:
            try:
                # O timeout ajuda a prevenir travamento do listener
                msg = await asyncio.wait_for(self.ws.recv(), timeout=10) 
                data = json.loads(msg)

                if data.get("error"):
                    # O erro de InvalidSymbol que você viu antes
                    print("[ERRO FATAL DERIV]:", data["error"])
                    # Se receber um erro, tenta continuar o loop (para evitar queda total)
                    continue 
                
                # Processamento de Ticks
                if data.get("msg_type") == "tick":
                    tick = data["tick"]
                    price = float(tick["quote"])
                    update_ticks(price) 
                    
                    print(f"[Deriv] ✅ Tick recebido: {price}") 
                    
                # Processamento de Saldos (para atualização em tempo real, se necessário)
                if data.get("msg_type") == "balance":
                     if data.get('balance'):
                        self.account_info['balance'] = data['balance'].get('balance', 0.0)

            except websockets.ConnectionClosed as e:
                print(f"[Deriv] Conexão fechada. Motivo: {e}. Desligando cliente.")
                self.connected = False
                break
            except asyncio.TimeoutError:
                # Envia um 'ping' para manter a conexão viva
                await self.ws.send(json.dumps({"ping": 1}))
                print("[Deriv] Ping enviado para manter conexão...") 
                continue
            except Exception as e:
                print(f"[ERRO GERAL] no listener: {e}")
                continue

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
