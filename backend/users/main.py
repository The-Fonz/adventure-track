import signal
import asyncio

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner

from .db import Db
from ..utils import BackendAppSession, getLogger

logger = getLogger('users.main')


class UsersComponent(BackendAppSession):

    async def onJoin(self, details):
        logger.info("session joined")

        db = await Db.create()
        self.db = db

        async def get_user_by_id(user_id):
            return await db.get_user_by_id(user_id)

        async def get_user_by_hash(user_id_hash):
            return await db.getuser(user_id_hash)

        async def get_user_id_by_hash(user_id_hash):
            "Returns only numeric user id"
            return await db.getuser_id(user_id_hash)

        async def get_user_hash_by_id(user_id):
            "Returns user hash"
            return await db.getuser_hash(user_id)

        async def check_user_authcode(user_id_hash, user_auth_code):
            return await db.check_auth(user_id_hash, user_auth_code)

        self.register(get_user_by_id, 'at.users.get_user_by_id')
        self.register(get_user_by_hash, 'at.users.get_user_by_hash')
        self.register(get_user_id_by_hash, 'at.users.get_user_id_by_hash')
        self.register(get_user_hash_by_id, 'at.users.get_user_hash_by_id')
        self.register(check_user_authcode, 'at.users.check_user_authcode')


if __name__=="__main__":
    UsersComponent.run_forever()
