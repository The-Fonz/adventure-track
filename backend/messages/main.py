import signal
import asyncio

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner

from .db import Db
from ..utils import getLogger

logger = getLogger('messages.main')


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

        async def fetchmsgs(user_id_hash):
            user_id = await self.call('at.users.get_user_id_by_hash', user_id_hash)
            return await db.getmsgs(user_id)

        self.register(fetchmsgs, 'at.messages.fetchmsgs')

        async def insertmsg(msgjson):
            logger.debug("Inserting message...")
            q = asyncio.Queue()
            user_id = msgjson['user_id']
            # Run while continuing this coroutine
            asyncio.ensure_future(db.insertmsg(msgjson, updatequeue=q))
            # Emit any updates caused by media rendering finishing
            user_id_hash = None
            first = True
            while True:
                logger.debug("Wait for update")
                update = await q.get()
                logger.debug("GET update")
                # Stop signal
                if update == None:
                    logger.debug("Stop signal")
                    break
                # Do this only once, updates are for only one user
                if not user_id_hash:
                    logger.debug("Getting user id hash")
                    user_id_hash = await self.call('at.users.get_user_hash_by_id', user_id)
                # Emit event on channel at.messages.user.<id_hash>
                userchannel = 'at.messages.user.{}'.format(user_id_hash)
                # For some reason this method is synchronous
                self.publish(userchannel, update)
                logger.debug("Published update on channel %s for user_id %s", userchannel, user_id)
                first = False
            if first:
                # Need to fail so WAMP caller gets notified
                # TODO: Return to caller on first update?
                # TODO: Find out if this crashes process or not
                raise Warning("No update received for message %s", msgjson)

        self.register(insertmsg, 'at.messages.insertmsg')

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
