import json
import asyncio

class TradeExecutor:
    def __init__(self, client):
        self.client = client

    async def execute_trade(self, action: str, amount: float, symbol: str = "R_100"):
        """
        Executa a ordem na Deriv após confirmação.
        action: 'CALL' ou 'PUT'
        """
        if not self.client or not self.client.authorized:
            return {"status": "error", "message": "Cliente não autorizado."}

        # Converte a ação para o formato da Deriv (CALL -> BUY / PUT -> SELL não, na Deriv é CALL/PUT)
        contract_type = "CALL" if "CALL" in action.upper() else "PUT"
        
        trade_msg = {
            "buy": 1,
            "subscribe": 1,
            "price": amount,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": contract_type,
                "currency": "USD",
                "duration": 1,
                "duration_unit": "m", # Duração de 1 minuto conforme estratégia
                "symbol": symbol
            }
        }

        try:
            await self.client.ws.send(json.dumps(trade_msg))
            return {"status": "success", "message": f"Ordem de {contract_type} enviada!"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
