import asyncio
import datetime

from autobahn.wamp.exception import ApplicationError
from aiohttp import web

from ...utils import BackendAppSession, getLogger

logger = getLogger('location.livetrack24.main')


async def site_factory(wampsess):
    """
    Creates aiohttp server listening on specified port
    :param wampsession:
    """

    async def client(request):
        "Should return 0 if invalid, otherwise user id integer"
        # We don't user password, can be anything
        # user_pass = request.query.get('pass')
        user_auth_code = request.query.get('user')
        if not user_auth_code:
            logger.info("No user or pass provided...")
            # Livetrack24 returns status 200 on basically any error
            return web.Response(status=200, text='0')
        try:
            user_id = await wampsess.call('at.users.get_user_id_by_authcode', user_auth_code)
        except ApplicationError:
            logger.exception("Could not reach user service!")
            return web.HTTPInternalServerError(reason="Internal communication error")
        if user_id:
            logger.info("Correct credentials for user id %s", user_id)
            # Send back actual user ID
            return web.Response(text=str(user_id), status=200)
        else:
            logger.info("Incorrect credentials or non-existing user, user_id: %s", user_id)
            return web.Response(text='0', status=200)

    async def track(request):
        "Track point as per the spec at http://www.livetrack24.com/docs/wiki/LiveTracking%20API"
        g = lambda n: request.query.get(n)
        leolive = g('leolive')
        sessionid = g('sid')
        if not sessionid:
            logger.info("No session ID")
            return web.Response(status=200, text="NOK : No session ID")
        # Ignore start/end track packets
        # Compare against string, not int!
        if leolive != '4':
            logger.info("Leolive is not 4 but %s", leolive)
            return web.Response(status=200)

        trackpt = {
            "source": 'mobile',
            # Rightmost 3 bits are user ID, see spec
            "user_id": int(sessionid) & 0x00ffffff,
            # Unix GPS timestamp in GMT
            "timestamp": datetime.datetime.utcfromtimestamp(int(g('tm'))).isoformat(),
            "ptz": {
                # Lat/lon in decimal notation
                "longitude": float(g('lon')),
                "latitude": float(g('lat')),
                # Altitude in meters above MSL (not geoid), no decimals
                "height_m_msl": float(g('alt'))
            },
            # Speed over ground in km/h, no decimals
            "speed_over_ground_kmh": float(g('sog')),
            # Course over ground in degrees 0-360, no decimals
            "course_over_ground_deg": float(g('cog'))
        }

        await wampsess.call('at.location.insert_gps_point', trackpt)
        return web.Response(status=200)

    app = web.Application()

    app.router.add_get(r'/client.php', client)
    app.router.add_get(r'/track.php', track)

    loop = asyncio.get_event_loop()

    await loop.create_server(app.make_handler(), '127.0.0.1', 5002)


class SiteComponent(BackendAppSession):

    async def onJoin(self, details):
        logger.info("session joined")
        await site_factory(self)


if __name__=="__main__":
    SiteComponent.run_forever()
