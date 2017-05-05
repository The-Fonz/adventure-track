from .db import Db
from ..utils import BackendAppSession, getLogger

logger = getLogger('adventures.main')


class AdventuresComponent(BackendAppSession):

    async def onJoin(self, details):
        logger.info("session joined")

        self.db = await Db.create()

        async def get_adventures(limit=None):
            limit = limit or 100
            return await self.db.get_adventures(limit=limit)

        self.register(get_adventures, 'at.adventures.get_adventures')

        async def get_adventure_by_hash(adv_hash):
            return await self.db.get_adventure_by_hash(adv_hash)

        self.register(get_adventure_by_hash, 'at.adventures.get_adventure_by_hash')


if __name__=="__main__":
    AdventuresComponent.run_forever()
