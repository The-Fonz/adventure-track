import asyncio
import datetime
from os import environ

import asyncpg
from sqlalchemy import MetaData, Table, Column, Integer, DateTime, create_engine

from ..utils import record_to_json, getLogger

logger = getLogger('telegrambot.db')

metadata = MetaData()

# Only used for table creation, no ORM
message = Table('users_telegram_link', metadata,
    # Unique id is not needed but nice when removing duplicates
    Column('id', Integer, primary_key=True),
    Column('created', DateTime),
    Column('user_id', Integer, unique=True, index=True),
    Column('telegram_id', Integer, unique=True, index=True)
)


class Db():
    @classmethod
    async def create(cls, loop=None):
        "Use like `await Db.create()` to enable use of async methods"
        db = Db()
        db.pool = await asyncpg.create_pool(dsn=environ["DB_URI_ATSITE"])
        return db

    async def get_link(self, user_id=None, telegram_id=None, existingconn=None):
        "Get tuple(user_id, telegram_id) by providing either user_id or telegram_id"
        if (not user_id and not telegram_id) or (user_id and telegram_id):
            raise Warning("Must provide either user_id or telegram_id")
        conn = existingconn or await self.pool.acquire()
        if user_id:
            link = await conn.fetchrow('SELECT * FROM users_telegram_link WHERE user_id=$1', user_id)
        elif telegram_id:
            link = await conn.fetchrow('SELECT * FROM users_telegram_link WHERE telegram_id=$1', telegram_id)
        if not existingconn:
            await self.pool.release(conn)
        if not link:
            return None
        return await record_to_json(link, exclude=('id', 'created'))

    async def insertlink(self, user_id, telegram_id, existingconn=None):
        conn = existingconn or await self.pool.acquire()
        timestamp = datetime.datetime.now()
        await conn.execute('INSERT INTO users_telegram_link (created, user_id, telegram_id) '
                           'VALUES ($1, $2, $3)', timestamp, user_id, telegram_id)
        if not existingconn:
            await self.pool.release(conn)


class RollbackException(Exception): pass


async def test_db_basics(db):
    "Not much to test, just the creation of links"
    async with db.pool.acquire() as conn:
        try:
            async with conn.transaction():
                # Negative id's don't exist so we can use them for testing
                user_id = -10
                telegram_id = -100
                await db.insertlink(user_id, telegram_id, existingconn=conn)
                l1 = await db.get_link(user_id=user_id, existingconn=conn)
                l2 = await db.get_link(telegram_id=telegram_id, existingconn=conn)
                assert l1['user_id'] == user_id
                assert l1['telegram_id'] == telegram_id
                assert l1 == l2
                # Non-existing link should return None
                l3 = await db.get_link(telegram_id=-120, existingconn=conn)
                assert l3 == None
                # Should throw when both args are given
                try:
                    await db.get_link(user_id=999, telegram_id=999)
                except Warning:
                    pass
                # Should throw when no args are given
                try:
                    await db.get_link()
                except Warning:
                    pass
                raise RollbackException
        except RollbackException:
            pass


if __name__=="__main__":
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)7s: %(message)s'
    )

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
        logger.info("Created tables")

    if args.test:
        l = asyncio.get_event_loop()
        db = l.run_until_complete(Db.create())
        try:
            l.run_until_complete(test_db_basics(db))
        finally:
            l.run_until_complete(l.shutdown_asyncgens())
            l.close()
        logger.info("Completed successfully")

