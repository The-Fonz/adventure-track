import signal
import asyncio

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner

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

    def onDisconnect(self):
        logger.warn("transport disconnected, stop updater and event loop...")
        # Prevent AttributeError if not joined
        if getattr(self, 'updater'):
            self.updater.stop()
        asyncio.get_event_loop().stop()



if __name__=="__main__":
    def stopcallback(protocol):
        # Clean up stuff if active session
        if protocol._session:
            logger.info("Stopping Telegram bot updater...")
            protocol._session.updater.stop()
        #     logger.info("Running protocol session leave")
        #     l.run_until_complete(protocol._session.leave())

    TelegramComponent.run_forever(stopcallback=stopcallback)
