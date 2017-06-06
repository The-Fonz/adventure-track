import asyncio
import aiohttp
import datetime

from ..utils import BackendAppSession, getLogger
from .db import Db

logger = getLogger('spotbot.main')

SPOT_API_URL = "https://api.findmespot.com/spot-main-web/consumer/rest-api/2.0/public/feed/{feed_id}/message.json"


async def parse_spot_msg(spot_msg, user_id):
    "From spot json msg to message that we can put in our own db"
    altitude = spot_msg.get('altitude')
    if altitude: altitude = float(altitude)
    msg = {
        'user_id': user_id,
        'spot_msg_id': int(spot_msg['id']),
        'spot_msg_type': spot_msg.get('messageType'), # CUSTOM TRACK OK
        'spot_msg_latitude': float(spot_msg['latitude']),
        'spot_msg_longitude': float(spot_msg['longitude']),
        'spot_msg_altitude': altitude, # 0 altitude is failure to acquire
        'spot_msg_battery_state': spot_msg.get('batteryState'), # GOOD or LOW
        'timestamp': datetime.datetime.utcfromtimestamp(spot_msg['unixTime']),
        'spot_msg': spot_msg
    }
    return msg


async def get_spot_api_msgs(feed_id):
    url = SPOT_API_URL.format(feed_id=feed_id)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 403:
                logger.exception("Shit, we hit SPOT API's rate limits!")
            elif resp.status != 200:
                logger.exception("Problem other than rate limits, status code %s", resp.status)
            else:
                feed = await resp.json()
                logger.debug(feed)
                try:
                    # No messages to display
                    if feed['response']['errors']['error']['code'] == 'E-0195':
                        logger.debug("No messages for feed %s", feed_id)
                        return []
                except KeyError:
                    pass
                msgs = feed['response']['feedMessageResponse']['messages']['message']
                return msgs



class SpotBotComponent(BackendAppSession):
    async def onJoin(self, details):
        """
        Listen to SPOT API as specified here:
        https://faq.findmespot.com/index.php?action=showEntry&data=69
        :param details: 
        :return: 
        """
        logger.info("Session joined")

        db = await Db.create()

        async def get_spot_msgs_by_user_id(user_id):
            return db.get_spot_msgs_by_user_id(user_id)

        self.register(get_spot_msgs_by_user_id, 'at.spotbot.get_spot_msgs_by_user_id')

        while True:
            # Find feed that needs to be queried
            # Get raw records, they have datetime as datetime
            links = await db.get_all_links(raw=True)
            for link in links:
                # Allow at least 2.5 minutes between calls of the same feed
                if (link['last_queried'] + datetime.timedelta(minutes=3)
                    < datetime.datetime.utcnow()):
                    logger.debug("Checking feed %s for user_id %s", link['feed_id'], link['user_id'])
                    spot_msgs = await get_spot_api_msgs(link['feed_id'])
                    await db.update_link_last_queried(link['id'])
                    if spot_msgs:
                        newcount = 0
                        for spot_msg in spot_msgs:
                            # Parse message content so it's easier to handle
                            msg = await parse_spot_msg(spot_msg, link['user_id'])
                            # Find out if message is new
                            msg_exists = await db.spot_msg_id_exists(link['user_id'], msg['spot_msg_id'])
                            if not msg_exists:
                                newcount += 1
                                # Insert into our own db
                                await db.insert_msg(msg)
                                # Any message has location, so we send them all to location service
                                trackpt = {
                                    "source": 'spot',
                                    "user_id": link['user_id'],
                                    "timestamp": msg['timestamp'].isoformat(),
                                    "ptz": {
                                        # Lat/lon in decimal notation
                                        "longitude": msg['spot_msg_longitude'],
                                        "latitude": msg['spot_msg_latitude'],
                                        # Altitude in meters above MSL (not geoid), no decimals
                                        "height_m_msl": msg['spot_msg_altitude']
                                    }
                                }
                                await self.call('at.location.insert_gps_point', trackpt)
                                # TODO: Handle CUSTOM or OK messages
                        logger.debug("Retrieved %s messages from feed %s, of which %s are new",
                                     len(spot_msgs), link['feed_id'], newcount)
            # Sleep for at least 2 seconds to avoid hitting rate limits
            await asyncio.sleep(2.5)


if __name__=="__main__":
    SpotBotComponent.run_forever()
