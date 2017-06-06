import datetime

from autobahn.wamp.exception import ApplicationError

from .db import Db
from ..utils import BackendAppSession, getLogger, convert_to_datetime

logger = getLogger('location.main')


class LocationComponent(BackendAppSession):

    async def onJoin(self, details):
        logger.info("session joined")

        db = await Db.create()
        self.db = db

        async def insert_gps_point(gps_pt):
            # Returns the point in the same format as db.get_gps_points_by_user_id
            gps_points = await db.insert_gps_point(gps_pt)
            # Now emit on personal channel
            user_id = gps_pt['user_id']
            try:
                user_id_hash = await self.call('at.users.get_user_hash_by_id', user_id)
                user_channel = 'at.public.location.user.{}'.format(user_id_hash)
                self.publish(user_channel, gps_points)
            except ApplicationError:
                logger.exception("Could not retrieve user id hash or emit gps point on personal channel")
            # And emit on adventure channel(s), if any
            try:
                # Get active adventures
                adventures = await self.call('at.adventures.get_adventures_by_user_id', user_id)
                # Only try to loop over adventures if there actually are any
                if adventures:
                    for adv in adventures:
                        adv_channel = 'at.public.location.adventure.{}'.format(adv['url_hash'])
                        self.publish(adv_channel, gps_points)
            except ApplicationError:
                logger.exception("Could not retrieve adventures for user_id or emit gps point on adventure channel")

        async def get_tracks_by_user_id_hash(user_id_hash):
            # TODO: Add start, end keywords
            user = await self.call('at.users.get_user_by_hash', user_id_hash)
            if not user:
                msg = "User id hash {} does not exist".format(user_id_hash)
                logger.warning(msg)
                # Will be caught by Autobahn and raised in client
                raise Warning(msg)
            user_id = user['id']
            return await db.get_gps_points_by_user_id(user_id)

        async def get_tracks_by_adventure_id_hash(adventure_id_hash):
            users = await self.call('at.adventures.get_users_by_adventure_url_hash', adventure_id_hash)
            adventure = await self.call('at.adventures.get_adventure_by_hash', adventure_id_hash)
            if users == None:
                raise Warning("Adventure does not exist!")
            elif users == []:
                raise Warning("No users found for adventure")
            else:
                out = []
                for user in users:
                    user_id = user['id']
                    # Make sure to use min/max datetime if start or stop is None
                    start = convert_to_datetime(adventure['start']) or datetime.datetime.min
                    end = convert_to_datetime(adventure['stop']) or datetime.datetime.max
                    gps_points = await db.get_gps_points_by_user_id(user_id, start=start, end=end)
                    # Do not append if None
                    if gps_points:
                        out.append(gps_points)
                return out

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
            pts_before = await self.db.get_gps_points_by_user_id(user_id, start=way_before, end=timestamp)
            pts_after = await self.db.get_gps_points_by_user_id(user_id, start=timestamp, end=way_after)
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
        self.register(get_tracks_by_adventure_id_hash, 'at.public.location.get_tracks_by_adventure_id_hash')


if __name__=="__main__":
    LocationComponent.run_forever()
