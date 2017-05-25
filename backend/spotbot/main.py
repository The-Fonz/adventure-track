import asyncio
import aiohttp
import datetime

from ..utils import BackendAppSession, getLogger
from .db import Db

logger = getLogger('spotbot.main')

SPOT_API_URL = "https://api.findmespot.com/spot-main-web/consumer/rest-api/2.0/public/feed/{feed_id}/message.json"


async def get_spot_api_msgs(feed_id):
    url = SPOT_API_URL.format(feed_id=feed_id)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 403:
                logger.exception("Shit, we hit SPOT API's rate limits!")
            else:
                feed = await resp.json()
                # TODO: Decode response
                msgs = feed['response']['feedMessageResponse']['messages']


class SpotBotComponent(BackendAppSession):
    async def onJoin(self, details):
        """
        Listen to SPOT API as specified here:
        https://faq.findmespot.com/index.php?action=showEntry&data=69
        :param details: 
        :return: 
        """
        logger.info("Session joined")

        db = Db()

        while True:
            # Find feed that needs to be queried
            # Get raw records, they have datetime as datetime
            for link in await db.get_all_links(raw=True):
                # Allow at least 2.5 minutes between calls of the same feed
                if (link['last_queried'] + datetime.timedelta(minutes=3)
                    < datetime.datetime.utcnow()):
                    msgs = await get_spot_api_msgs(link['feed_id'])
                    # TODO: Store in db
            # Sleep for at least 2 seconds to avoid hitting rate limits
            asyncio.sleep(2.5)


if __name__=="__main__":
    SpotBotComponent.run_forever()
