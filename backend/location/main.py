from .db import Db
from ..utils import BackendAppSession, getLogger

logger = getLogger('location.main')


class LocationComponent(BackendAppSession):

    async def onJoin(self, details):
        logger.info("session joined")

        db = await Db.create()
        self.db = db

        async def insert_gps_point(gps_pt):
            return await db.insert_gps_point(gps_pt)

        async def get_tracks_by_user_id_hash(user_id_hash):
            # TODO: Add start, end keywords
            user = await self.call('at.users.get_user_by_hash', user_id_hash)
            if not user:
                msg = "User id hash {} does not exist".format(user_id_hash)
                logger.warning(msg)
                # Will be caught by Autobahn and raised in client
                raise Warning(msg)
            user_id = user['id']
            return await db.get_gps_points(user_id)


        self.register(insert_gps_point, 'at.location.insert_gps_point')
        self.register(get_tracks_by_user_id_hash, 'at.public.location.get_tracks_by_user_id_hash')


if __name__=="__main__":
    LocationComponent.run_forever()
