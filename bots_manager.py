# bots_manager.py

import uuid
from typing import Dict, Any, List

class BotsManager:
    
    def __init__(self):
        self.active_bots: Dict[str, Any] = {}
        
    def create_bot(self, spec: Dict[str, Any]) -> str:
        """Cria um novo bot e o armazena."""
        bot_id = str(uuid.uuid4())
        
        new_bot = {
            "id": bot_id,
            "name": spec.get("name", "Bot Padrão"),
            "symbol": spec.get("symbol", "V100"),
            "tf": spec.get("tf", "5"),
            "stop_loss": spec.get("stop_loss", 5.0), 
            "take_profit": spec.get("take_profit", 10.0), 
            "is_active": False, # Inicia inativo
            "current_balance": 0.0, 
            "operations_log": []
        }
        self.active_bots[bot_id] = new_bot
        print(f"[BotsManager] Bot criado: {new_bot['name']} ({bot_id[:4]}...)")
        return bot_id

    def list_bots(self) -> List[Dict[str, Any]]:
        """Retorna a lista de todos os bots."""
        return list(self.active_bots.values())

    def get_bot(self, bot_id: str) -> Dict[str, Any] or None:
        """Retorna a configuração de um bot específico."""
        return self.active_bots.get(bot_id)

    def activate_bot(self, bot_id: str) -> Dict[str, Any] or None:
        """Define o status do bot como ATIVO."""
        bot = self.get_bot(bot_id)
        if bot:
            bot["is_active"] = True
            print(f"[BotsManager] Bot ATIVADO: {bot['name']}")
        return bot

    def deactivate_bot(self, bot_id: str) -> Dict[str, Any] or None:
        """Define o status do bot como INATIVO."""
        bot = self.get_bot(bot_id)
        if bot:
            bot["is_active"] = False
            print(f"[BotsManager] Bot DESATIVADO: {bot['name']}")
        return bot
