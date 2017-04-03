import asyncio
import datetime
from os import environ
import json

import asyncpg
from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, Text, create_engine
from sqlalchemy.dialects.postgresql import JSONB

from .mediaconfig import video_resolutions, image_resolutions
from .transcode import video_transcode, image_transcode, audio_transcode

metadata = MetaData()

# Only used for table creation, no ORM
message = Table('message', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer),
    # Time that message was created (e.g. video file time)
    Column('timestamp', DateTime, nullable=True),
    # Time that message was received by server
    Column('received', DateTime),
    # Might be a video or voice message, so title/text can be omitted
    Column('title', Text, nullable=True),
    Column('text', Text, nullable=True),
    # Store original file path, max. path size is 255 on most systems
    Column('image_original', String(255), nullable=True),
    # Store many different versions of media like
    # {"lowres": "/some-path", "highres": "/some-path"}
    Column('image_versions', JSONB, nullable=True),
    Column('video_original', String(255), nullable=True),
    # Postgres' JSONB is queryable
    Column('video_versions', JSONB, nullable=True),
    Column('audio_original', String(255), nullable=True),
    Column('audio_versions', JSONB, nullable=True),
    # Store original Telegram message json for later analysis
    Column('telegram_message', JSONB, nullable=True)
)


async def record_to_json(records):
    "Converts list of asyncpg.Record to json"
    out = []
    # Can make async using await asyncio.sleep(0) but should be real fast
    for r in records:
        recdict = {}
        for k,v in r.items():
            # Parse jsonb if not empty
            if v and k in set(('video_versions', 'image_versions', 'audio_versions')):
                v = json.loads(v)
            recdict[k] = v
        out.append(recdict)
    return out


class Db():
    @classmethod
    async def create(self, loop=None, num_video_queues=2):
        "Use like `await Db.create()` to enable use of async methods"
        self = Db()
        self.pool = await asyncpg.create_pool(dsn=environ["DB_URI_ATSITE"])
        # Set up transcoding consumers
        if not loop:
            loop = asyncio.get_event_loop()
        # Priority queue enables processing low-quality first
        self.video_queue = asyncio.PriorityQueue()
        # Set up as many queue consumers as desired
        self.num_video_queues = num_video_queues
        for i in range(num_video_queues):
            loop.create_task(video_transcode(self.video_queue))
        # Image and audio should be real fast, so just use one consumer
        self.image_queue = asyncio.PriorityQueue()
        loop.create_task(image_transcode(self.image_queue))
        self.audio_queue = asyncio.PriorityQueue()
        loop.create_task(audio_transcode(self.audio_queue))
        return self

    async def getmsgs(self, user_id, existingconn=None):
        # Allow passing in an existing connection for unittesting
        conn = existingconn or await self.pool.acquire()
        recs = await conn.fetch('SELECT * FROM message WHERE user_id=$1', user_id)
        out = await record_to_json(recs)
        # Release acquired connection
        if not existingconn:
            self.pool.release(conn)
        return out

    async def insertmsg(self, msgjson, existingconn=None):
        """
        Parses msg json and inserts into db.
        Transcodes any video/image/audio.
        Yields updates so caller can notify listeners.
        """
        user_id = msgjson['user_id']
        timestamp = msgjson['timestamp']
        received = datetime.datetime.now()
        title = msgjson['title']
        text = msgjson['text']
        video_original = msgjson.get('video_original', None)
        image_original = msgjson.get('image_original', None)
        audio_original = msgjson.get('audio_original', None)
        conn = existingconn or await self.pool.acquire()
        # Let Postgres return generated id and fetch its value
        id = await conn.fetchval('''
        INSERT INTO message (id, user_id, timestamp, received, title, text, video_original, image_original, audio_original)
        VALUES (DEFAULT, $1, $2, $3, $4, $5, $6, $7, $8) RETURNING id
        ''', user_id, timestamp, received, title, text, video_original, image_original, audio_original)
        futs = []
        if video_original:
            for i, res in enumerate(video_resolutions):
                fut = asyncio.Future()
                # Lowest res (fast encode) gets highest prio
                print("put on q")
                await self.video_queue.put((i, fut, res))
                futs.append(fut)
        if image_original:
            for i, res in enumerate(image_resolutions):
                fut = asyncio.Future()
                await self.image_queue.put((i, fut, res))
                futs.append(fut)
        if audio_original:
            raise Warning("Audio transcode not implemented")
            pass

        if futs:
            for fut in asyncio.as_completed(futs):
                print("await fut")
                res = await fut
                # Future's result is set to json describing transcode outcome
                mediav = "{}_versions".format(res['mediatype'])
                # Get existing versions
                versions = await conn.fetchval(
                # Cannot be an arg so just join string like this
                "SELECT "+mediav+" FROM message WHERE id=$1"
                , id)
                # Empty dict if no versions defined yet
                versions = json.loads(versions) if versions else {}
                # Add new versions
                versions.update(res['versions'])
                # Update db
                await conn.execute(
                "UPDATE message SET "+mediav+"=$2::jsonb WHERE id=$1"
                , id, json.dumps(versions))
                # Notify listeners now that at least one media type has been added
                # TODO: notify by yielding (async generators only available from Py3.6)
        if not existingconn:
            self.pool.release(conn)
        return id

    async def finish_queues(self):
        # Send stop signal as lowest prio
        for i in range(self.num_video_queues):
            await self.video_queue.put((float('inf'), None))
        await self.image_queue.put((float('inf'),None))
        await self.audio_queue.put((float('inf'),None))
        print("Waiting for transcode queues to empty...")
        asyncio.wait([self.video_queue,
                      self.image_queue,
                      self.audio_queue])


class RollbackException(Exception): pass


async def test_db_basics(db):
    "Test basic message saving"
    # Use non-occurring negative value as user id
    intmin = -2147483648
    async with db.pool.acquire() as conn:
        try:
            # Use nested transactions to easily roll back later
            async with conn.transaction():
                # No messages for non-existing user
                msgs = await db.getmsgs(intmin, existingconn=conn)
                assert msgs == []
                msgjson = {
                    'user_id': intmin,
                    'timestamp': datetime.datetime.now(),
                    'received': datetime.datetime.now(),
                    'title': 'Titre',
                    'text': 'Bodytext'}
                id = await db.insertmsg(msgjson, existingconn=conn)
                msgs = await db.getmsgs(intmin, existingconn=conn)
                print('id={}'.format(id))
                assert len(msgs) == 1
                assert msgs[0]['title'] == 'Titre'
                # Roll back transaction
                raise RollbackException
        except RollbackException:
            pass

async def test_db_media(db):
    "Test media conversion"
    intmin = -2147483648
    async with db.pool.acquire() as conn:
        try:
            async with conn.transaction():
                msgjson = {
                    'user_id': intmin,
                    'timestamp': datetime.datetime.now(),
                    'received': datetime.datetime.now(),
                    'title': 'Titre',
                    'text': 'Bodytext',
                    'video_original': '/path/to/video',
                }
                id = await db.insertmsg(msgjson, existingconn=conn)
                msgs = await db.getmsgs(intmin, existingconn=conn)
                print('id={}'.format(id))
                assert len(msgs) == 1
                msg = msgs[0]
                print(msg)
                assert msg['video_versions'] == {'hi': 'there'}
                raise RollbackException
        except RollbackException:
            pass


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--create', action='store_true',
                        help="Create database tables")
    parser.add_argument('--test', action='store_true',
                        help="Test on real db using nested transactions")
    args = parser.parse_args()

    if args.create:
        engine = create_engine(environ["DB_URI_ATSITE"])
        metadata.create_all(engine)
        print("Created tables")

    if args.test:
        import asyncio
        l = asyncio.get_event_loop()
        db = l.run_until_complete(Db.create())
        try:
            l.run_until_complete(test_db_basics(db))
            l.run_until_complete(test_db_media(db))
        finally:
            l.run_until_complete(db.finish_queues())
            l.run_until_complete(l.shutdown_asyncgens())
            l.close()
        print("Tests completed successfully")
