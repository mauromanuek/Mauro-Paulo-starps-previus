# bots_manager.py
# Gerenciador simples de bots (não persiste nada)

import datetime
import uuid

class BotsManager:

    def __init__(self):
        self.bots = {}

    def create_bot(self, spec: dict):
        bot_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat()

        bot = {
            "id": bot_id,
            "name": spec.get("name"),
            "active": False,
            "simulate": spec.get("mode", "sandbox") == "sandbox",
            "spec": spec,
            "created_at": now,
            "activated_at": None,
            "deactivated_at": None,
            "stats": {"trades": 0, "wins": 0, "losses": 0},
            "logs": [],
        }

        self.bots[bot_id] = bot
        return bot_id

    def list_bots(self):
        return list(self.bots.values())

    def get_bot(self, bot_id: str):
        return self.bots.get(bot_id)

    def activate_bot(self, bot_id: str, simulate=True):
        bot = self.get_bot(bot_id)
        if not bot:
            return None

        bot["active"] = True
        bot["simulate"] = simulate
        bot["activated_at"] = datetime.datetime.utcnow().isoformat()
        bot["logs"].append({"event": "activated", "at": bot["activated_at"]})

        return bot

    def deactivate_bot(self, bot_id: str):
        bot = self.get_bot(bot_id)
        if not bot:
            return None

        bot["active"] = False
        bot["deactivated_at"] = datetime.datetime.utcnow().isoformat()
        bot["logs"].append({"event": "deactivated", "at": bot["deactivated_at"]})

        return bot
