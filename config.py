import json
import asyncio

class TradeExecutor:
    def __init__(self, client):
        self.client = client
        self.last_result = None

    async def execute_trade(self, action: str, amount: float, symbol: str = "R_100"):
        """Executa a ordem na Deriv via WebSocket"""
        if not self.client or not self.client.authorized:
            return {"status": "error", "message": "Cliente não autorizado."}

        # Deriv usa CALL para Compra e PUT para Venda
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
                "duration_unit": "m",
                "symbol": symbol
            }
        }

        try:
            await self.client.ws.send(json.dumps(trade_msg))
            return {"status": "success", "message": f"Ordem {contract_type} enviada!", "type": contract_type}
        except Exception as e:
            return {"status": "error", "message": str(e)}
