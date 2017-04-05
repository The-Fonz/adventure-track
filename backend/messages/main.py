import logging
import signal
import asyncio

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner

from .db import Db

logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)7s: %(asctime)s %(name)s:%(lineno)s %(message)s'
)
logger = logging.getLogger('messages.main')


class MessagesComponent(ApplicationSession):
    def __init__(self, config=None):
        ApplicationSession.__init__(self, config)
        logger.info("component created")

    # def onConnect(self):
    #     logger.info("transport connected")
    #     self.join(self.config.realm)

    def onChallenge(self, challenge):
        logger.info("authentication challenge received")

    async def onJoin(self, details):
        logger.info("session joined")

        db = await Db.create()
        self.db = db

        async def fetchmsgs(user_id):
            return await db.getmsgs(user_id)

        self.register(fetchmsgs, 'com.messages.fetchmsgs')

        def insertmsg(msgjson):
            # Save in db
            pass

        # register insert msg

        # Publish on insert message

    # def onLeave(self, details):
    #     logger.info("session left")
    #
    # def onDisconnect(self):
    #     logger.info("transport disconnected")


if __name__=="__main__":

    l = asyncio.get_event_loop()

    runner = ApplicationRunner(url="ws://localhost:8080/ws", realm="realm1")
    # ApplicationRunner starts asyncio loop, and adds SIGTERM handler
    # Takes standard event loop
    protocol = runner.run(MessagesComponent, start_loop=False)

    l.add_signal_handler(signal.SIGINT, l.stop)
    l.add_signal_handler(signal.SIGTERM, l.stop)

    l.run_forever()
    logger.info("Loop stopped")

    logger.info("Finish db transcode queues")
    l.run_until_complete(protocol._session.db.finish_queues())

    # Clean up stuff after loop stops
    # if protocol._session:
    #     logger.info("Running protocol session leave")
    #     l.run_until_complete(protocol._session.leave())

    l.run_until_complete(l.shutdown_asyncgens())
    l.close()
    logger.info("Loop closed")
