import datetime

from .db import Db
from ..utils import BackendAppSession, getLogger, convert_to_datetime

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

        async def guess_coords_by_user_id(user_id, timestamp):
            """
            Interpolate user location by finding location within
            60 minutes from message timestamp. This gives a 120-minute window.
            If multiple points are found, linearly interpolate between them.
            """
            timestamp = convert_to_datetime(timestamp)
            way_before = timestamp - datetime.timedelta(minutes=-60)
            way_after = timestamp + datetime.timedelta(minutes=60)
            # Will return None if no pts found
            pts_before = await self.db.get_gps_points(user_id, start=way_before, end=timestamp)
            pts_after = await self.db.get_gps_points(user_id, start=timestamp, end=way_after)
            if not pts_before and not pts_after:
                return None
            # If only points before timestamp known, take last of prev pts
            if pts_before and not pts_after:
                return pts_before['coordinates'][-1]
            # If only points after timestamp known, take first next pt
            if not pts_before and pts_after:
                return pts_after['coordinates'][0]
            # If both points before and after timestamp known, linearly interpolate
            timestamp_lastpt_before = convert_to_datetime(pts_before['timestamps'][-1])
            timestamp_firstpt_after = convert_to_datetime(pts_after['timestamps'][0])
            # How far between points this timestamp lies
            a = (timestamp - timestamp_lastpt_before) / (timestamp_lastpt_before + timestamp_firstpt_after)
            # Coordinates of points between which timestamp lies
            p1 = pts_before['coordinates'][-1]
            p2 = pts_after['coordinates'][0]
            return [a * (p2[0]-p1[0]) + p1[0],
                    a * (p2[1]-p1[1]) + p1[1]]


        self.register(insert_gps_point, 'at.location.insert_gps_point')
        self.register(get_tracks_by_user_id_hash, 'at.public.location.get_tracks_by_user_id_hash')
        self.register(guess_coords_by_user_id, 'at.location.guess_coords_by_user_id')


if __name__=="__main__":
    LocationComponent.run_forever()
