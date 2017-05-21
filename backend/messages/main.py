import datetime

from autobahn.wamp.exception import ApplicationError

from .db import Db
from ..utils import BackendAppSession, getLogger

logger = getLogger('messages.main')


class MessagesComponent(BackendAppSession):

    async def onJoin(self, details):
        logger.info("session joined")

        db = await Db.create()
        self.db = db

        async def uniquemsgs(n=5):
            return await db.uniquemsgs(n=n)

        async def get_msgs_by_user_id(user_id_hash):
            user_id = await self.call('at.users.get_user_id_by_hash', user_id_hash)
            return await db.getmsgs(user_id, exclude_sensitive=True)

        async def get_msgs_by_adventure_hash(adventure_url_hash):
            out = []
            # Get adventure ID first
            adv = await self.call('at.adventures.get_adventure_by_hash', adventure_url_hash)
            if not adv:
                raise Warning("Adventure not found")
            adv_id = adv['id']
            # Now get all links with users
            links = await self.call('at.adventures.get_adventure_links_by_adv_id', adv_id)
            logger.debug("Found %s links for adventure id=%s name=%s", len(links), adv_id, adv['name'])
            # Get all user content from start of adventure to end
            for link in links:
                user_id = link['user_id']
                role = link['role']
                # Make sure to set values if the value of adv['start'] is None
                start = adv.get('start') or datetime.datetime.min
                end = adv.get('stop') or datetime.datetime.max
                msgs = await db.getmsgs(user_id, start=start, end=end, exclude_sensitive=True)
                logger.debug("Found %s messages for user id=%s in adventure id=%s start=%s end=%s", len(msgs), user_id, adv_id, start, end)
                out.extend(msgs)
            return out

        async def pub_msg_update(msg_id):
            msg = await db.getmsg(msg_id, exclude_sensitive=True)
            # First emit on user channel
            try:
                user_id_hash = await self.call('at.users.get_user_hash_by_id', msg['user_id'])
                # Emit event on channel at.messages.user.<id_hash>
                userchannel = 'at.messages.user.{}'.format(user_id_hash)
                # For some reason this method is synchronous
                self.publish(userchannel, msg)
                logger.debug("Published message id=%s on channel %s for user_id %s", msg_id, userchannel, msg['user_id'])
            except ApplicationError:
                logger.exception("Failed to retrieve user hash or publish update")
            # Now emit on adventure channel(s)
            try:
                now = datetime.datetime.now().isoformat()
                # Only get adventures that are currently active
                advs = await self.call('at.adventures.get_adventures_by_user_id', msg['user_id'], active_at=now)
                if advs:
                    for adv in advs:
                        adv_channel = 'at.messages.adventure.{}'.format(adv['url_hash'])
                        self.publish(adv_channel, msg)
                        logger.debug("Published message id=%s on channel %s for user_id %s", msg_id, adv_channel, msg['user_id'])
            except ApplicationError:
                logger.exception("Failed to retrieve adventures or publish update")


        async def insertmsg(msg):
            logger.debug("Inserting message...")
            msg_id = await db.insertmsg(msg)
            # Extract media and send all necessary info to transcode service
            nomedia = True
            media = []
            media_base = {'msg_id': msg_id}
            if msg.get('video_original'):
                media += [dict(media_base, type='video', path=msg['video_original'])]
                nomedia = False
            if msg.get('image_original'):
                media += [dict(media_base, type='image', path=msg['image_original'])]
                nomedia = False
            if msg.get('audio_original'):
                media += [dict(media_base, type='audio', path=msg['audio_original'])]
                nomedia = False
            # Save originals in db
            for m in media:
                await self.db.insertmedia(dict(m, original=True))
                await self.call('at.transcode.transcode', m)
            # Update only if message has no media, otherwise wait for media to be transcoded
            if nomedia:
                await pub_msg_update(msg_id)

        async def insertmedia(media):
            await db.insertmedia(media)
            # Update not when explicitly indicated in mediaconfig
            if media.get('update', True):
                await pub_msg_update(media['msg_id'])

        self.register(uniquemsgs, 'at.messages.uniquemsgs')
        self.register(get_msgs_by_user_id, 'at.public.messages.fetchmsgs')
        self.register(get_msgs_by_adventure_hash, 'at.public.messages.get_msgs_by_adventure_hash')
        self.register(insertmsg, 'at.messages.insertmsg')
        self.subscribe(insertmedia, 'at.transcode.finished')


if __name__=="__main__":
    MessagesComponent.run_forever()
