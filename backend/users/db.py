import logging
import asyncio
import datetime
from os import environ
import json

import dateutil.parser
import asyncpg
from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, Text, create_engine
from sqlalchemy.dialects.postgresql import JSONB, CHAR

from ..utils import record_to_json, friendlyhash

logger = logging.getLogger('users.db')

metadata = MetaData()

# Only used for table creation, no ORM
# Avoid clashing with 'user' builtin name
message = Table('users', metadata,
    Column('id', Integer, primary_key=True),
    # Friendly ID for URL's and personal page
    Column('id_hash', CHAR(8), unique=True, index=True),
    # Time that user was created
    Column('created', DateTime),
    Column('first_name', String(255), nullable=True),
    Column('last_name', String(255), nullable=True),
    Column('email', String(255), nullable=True),
    Column('telephone_mobile', String(255), nullable=True),
)


class Db():
    @classmethod
    async def create(cls, loop=None):
        "Use like `await Db.create()` to enable use of async methods"
        db = Db()
        db.pool = await asyncpg.create_pool(dsn=environ["DB_URI_ATSITE"])
        return db

    async def getuser(self, id_hash, existingconn=None):
        conn = existingconn or await self.pool.acquire()
        user = await conn.fetchrow('SELECT * FROM users WHERE id_hash=$1', id_hash)
        if not existingconn:
            await self.pool.release(conn)
        return await record_to_json(user)

    async def getuser_id(self, id_hash, existingconn=None):
        conn = existingconn or await self.pool.acquire()
        user_id = await conn.fetchval('SELECT id FROM users WHERE id_hash=$1', id_hash)
        if not existingconn:
            await self.pool.release(conn)
        return user_id

    async def insertuser(self, userjson, id_hash=None, id_hash_collision_retry=False, existingconn=None):
        "Make new user based on json representation"
        conn = existingconn or await self.pool.acquire()
        u = dict()
        u['id_hash'] = id_hash or await friendlyhash()
        created = userjson.get('created', datetime.datetime.now())
        # Parse if ISO string time
        u['created'] = created if type(created) == datetime.datetime else dateutil.parser.parse(created)
        u['first_name'] = userjson.get('first_name')
        u['last_name'] = userjson.get('last_name')
        u['email'] = userjson['email']
        u['telephone_mobile'] = userjson.get('telephone_mobile')
        async def ins(u):
            return await conn.fetchval('''
            INSERT INTO users (id, id_hash, created, first_name, last_name, email, telephone_mobile)
            VALUES (DEFAULT, $1, $2, $3, $4, $5, $6) RETURNING id
            ''', u['id_hash'], u['created'], u['first_name'], u['last_name'], u['email'], u['telephone_mobile'])
        # We need to handle friendly hash collisions
        for i in range(100):
            if i == 99:
                raise Exception("Impossible!")
            try:
                # Use nested transaction such that only this block fails and we can still use conn
                async with conn.transaction():
                    id = await ins(u)
                break
            except asyncpg.exceptions.UniqueViolationError as e:
                # Warn caller if id given
                if id_hash and not id_hash_collision_retry:
                    logger.error("Given id_hash already exists!")
                    raise e
                # Retry if self-chosen
                logger.warning("id_hash %s already exists, retry %s with another id", id_hash, i+1)
                u['id_hash'] = await friendlyhash()

        if not existingconn:
            await self.pool.release(conn)
        return id


class RollbackException(Exception): pass


async def test_db_basics(db):
    "Test user saving"
    async with db.pool.acquire() as conn:
        try:
            async with conn.transaction():
                # Hashids never makes swear words so we can be positive that this uid does not exist...
                u = await db.getuser('fuckcunt', existingconn=conn)
                assert u == None
                fh = await friendlyhash()
                user_1 = {
                    'first_name': "Fonz",
                    'last_name': "the Lion",
                    'email': 'hi@there431-9581345098-2435.com',
                    'telephone_mobile': '023535-1029213890'
                }
                await db.insertuser(user_1, id_hash=fh, existingconn=conn)
                u = await db.getuser(fh, existingconn=conn)
                assert u['first_name'] == "Fonz"
                # Insert identical id_hash with retry
                await db.insertuser(user_1, id_hash=fh, id_hash_collision_retry=True, existingconn=conn)
                # Insert identical id_hash
                try:
                    await db.insertuser(user_1, id_hash=fh, existingconn=conn)
                    raise Warning("Did not throw unique error!")
                except asyncpg.exceptions.UniqueViolationError:
                    pass
                # Can't do anything after this, will throw asyncpg.exceptions.InFailedSQLTransactionError
                raise RollbackException
        except RollbackException:
            pass


if __name__=="__main__":
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
    parser.add_argument('--importusers',
                        help="Import json file with list of users into db")
    args = parser.parse_args()

    if args.create:
        engine = create_engine(environ["DB_URI_ATSITE"])
        metadata.create_all(engine)
        logger.info("Created tables")

    if args.test or args.importusers:
        l = asyncio.get_event_loop()
        db = l.run_until_complete(Db.create())
        try:
            if args.test:
                l.run_until_complete(test_db_basics(db))
            elif args.importusers:
                with open(args.importusers, 'r') as f:
                    users = json.load(f)
                if not 'y' in input("Continue loading {} messages? [y/N] ".format(len(users))).lower():
                    raise Warning("Exiting...")
                coros = [db.insertuser(u) for u in users]
                l.run_until_complete(asyncio.wait(coros))
                logger.info("Inserted all users")
        finally:
            l.run_until_complete(l.shutdown_asyncgens())
            l.close()
        logger.info("Completed successfully")
