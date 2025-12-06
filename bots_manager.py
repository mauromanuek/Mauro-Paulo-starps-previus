import uuid
from bot import Bot

class BotsManager:
    def __init__(self, deriv):
        self.deriv = deriv
        self.bots = {}

    def create_bot(self, spec):
        bot_id = str(uuid.uuid4())
        bot = Bot(bot_id, spec, self.deriv)
        self.bots[bot_id] = bot
        return bot_id

    def list_bots(self):
        arr = []
        for bot_id, bot in self.bots.items():
            arr.append({
                "id": bot_id,
                "spec": bot.spec,
                "active": bot.active,
                "stats": bot.stats
            })
        return arr

    def activate_bot(self, bot_id):
        bot = self.bots.get(bot_id)
        if bot:
            bot.start()
            return True
        return False

    async def deactivate_bot(self, bot_id):
        bot = self.bots.get(bot_id)
        if bot:
            await bot.stop()
            return True
        return False
