import signal
import asyncio

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner

from .db import Db
from ..utils import getLogger
from .bot import main as bot_main

logger = getLogger('telegrambot.main')


class TelegramComponent(ApplicationSession):
    def __init__(self, config=None):
        ApplicationSession.__init__(self, config)
        logger.info("component created")

    def onChallenge(self, challenge):
        logger.info("authentication challenge received")

    async def onJoin(self, details):
        logger.info("session joined")

        self.db = await Db.create()

        # Create and run bot
        self.updater = bot_main(self, asyncio.get_event_loop())
        logger.info("bot is running")

    def onDisconnect(self):
        logger.warn("transport disconnected, stop updater and event loop...")
        self.updater.stop()
        asyncio.get_event_loop().stop()



if __name__=="__main__":

    l = asyncio.get_event_loop()

    runner = ApplicationRunner(url="ws://localhost:8080/ws", realm="realm1")
    protocol = runner.run(TelegramComponent, start_loop=False)

    l.add_signal_handler(signal.SIGINT, l.stop)
    l.add_signal_handler(signal.SIGTERM, l.stop)

    l.run_forever()
    logger.info("Loop stopped")

    # Clean up stuff if active session
    if protocol._session:
        protocol._session.updater.stop()
    #     logger.info("Running protocol session leave")
    #     l.run_until_complete(protocol._session.leave())

    l.close()
    logger.info("Loop closed")
