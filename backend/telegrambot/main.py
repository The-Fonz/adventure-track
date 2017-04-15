import asyncio

from .db import Db
from ..utils import BackendAppSession, getLogger
from .bot import main as bot_main

logger = getLogger('telegrambot.main')


class TelegramComponent(BackendAppSession):

    async def onJoin(self, details):
        logger.info("session joined")

        self.db = await Db.create()

        # Create and run bot
        self.updater = bot_main(self, asyncio.get_event_loop())
        logger.info("bot is running")

    async def cleanup(self, loop):
        logger.info("Cleaning up, stop updater...")
        # Prevent AttributeError if not joined
        if getattr(self, 'updater'):
            self.updater.stop()


if __name__=="__main__":
    TelegramComponent.run_forever()
