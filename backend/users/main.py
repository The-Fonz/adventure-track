import signal
import asyncio

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner

from .db import Db
from ..utils import getLogger

logger = getLogger('users.main')


class UsersComponent(ApplicationSession):
    def __init__(self, config=None):
        ApplicationSession.__init__(self, config)
        logger.info("component created")

    def onChallenge(self, challenge):
        logger.info("authentication challenge received")

    async def onJoin(self, details):
        logger.info("session joined")

        db = await Db.create()
        self.db = db

        async def getuser_hash(user_id_hash):
            return await db.getuser(user_id_hash)

        async def getuser_hash_id(user_id_hash):
            "Returns only numeric user id"
            return await db.getuser_id(user_id_hash)

        self.register(getuser_hash, 'at.users.getuser_hash')
        self.register(getuser_hash_id, 'at.users.getuser_hash_id')


if __name__=="__main__":

    l = asyncio.get_event_loop()

    runner = ApplicationRunner(url="ws://localhost:8080/ws", realm="realm1")
    protocol = runner.run(UsersComponent, start_loop=False)

    l.add_signal_handler(signal.SIGINT, l.stop)
    l.add_signal_handler(signal.SIGTERM, l.stop)

    l.run_forever()
    logger.info("Loop stopped")

    # Clean up stuff after loop stops
    # if protocol._session:
    #     logger.info("Running protocol session leave")
    #     l.run_until_complete(protocol._session.leave())

    l.run_until_complete(l.shutdown_asyncgens())
    l.close()
    logger.info("Loop closed")
