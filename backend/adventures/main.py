import datetime

from .db import Db
from ..utils import BackendAppSession, getLogger, convert_to_datetime

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

        async def get_adventure_links_by_adv_id(adv_id):
            return await self.db.get_adventure_links(adv_id)

        self.register(get_adventure_links_by_adv_id, 'at.adventures.get_adventure_links_by_adv_id')

        async def get_adventures_by_user_id(user_id, active_at=None):
            links = await self.db.get_adventure_user_links_by_user_id(user_id)
            if not links:
                return None
            out = []
            # Fetch adventure for every link
            for link in links:
                adv = await self.db.get_adventure_by_id(link['adventure_id'])
                # Filter on active
                if active_at:
                    start = convert_to_datetime(adv.get('start') or datetime.datetime.min)
                    stop = convert_to_datetime(adv.get('stop') or datetime.datetime.max)
                    active_at = convert_to_datetime(active_at)
                    if start < active_at < stop:
                        out.append(adv)
                else:
                    out.append(adv)
            return out

        self.register(get_adventures_by_user_id, 'at.adventures.get_adventures_by_user_id')

        async def public_get_users_by_adventure_url_hash(adv_hash):
            # First retrieve adventure id
            adv = await self.db.get_adventure_by_hash(adv_hash)
            # Now get all user links
            links = await self.db.get_adventure_links(adv['id'])
            out = []
            # Get all users that these links refer to
            for link in links:
                usr = await self.call('at.users.get_user_by_id', link['user_id'])
                out.append(usr)
            logger.debug("Returned %s users for adventure id=%s", len(out), adv['id'])
            return out

        self.register(public_get_users_by_adventure_url_hash, 'at.public.adventures.get_users_by_adventure_url_hash')


if __name__=="__main__":
    AdventuresComponent.run_forever()
