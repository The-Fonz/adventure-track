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

        async def fetchmsgs(user_id_hash):
            user_id = await self.call('at.users.get_user_id_by_hash', user_id_hash)
            return await db.getmsgs(user_id, exclude_sensitive=True)

        async def pub_msg_update(msg_id):
            msg = await db.getmsg(msg_id, exclude_sensitive=True)
            try:
                user_id_hash = await self.call('at.users.get_user_hash_by_id', msg['user_id'])
                # Emit event on channel at.messages.user.<id_hash>
                userchannel = 'at.messages.user.{}'.format(user_id_hash)
                # For some reason this method is synchronous
                self.publish(userchannel, msg)
                logger.debug("Published update on channel %s for user_id %s", userchannel, msg['user_id'])
            except ApplicationError:
                logger.exception("Failed to retrieve user hash or publish update")

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
        self.register(fetchmsgs, 'at.public.messages.fetchmsgs')
        self.register(insertmsg, 'at.messages.insertmsg')
        self.subscribe(insertmedia, 'at.transcode.finished')


if __name__=="__main__":
    MessagesComponent.run_forever()
