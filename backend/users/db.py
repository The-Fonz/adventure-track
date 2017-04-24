import logging
import asyncio
import datetime
from os import environ
import json

import dateutil.parser
import asyncpg

from ..utils import record_to_dict, friendlyhash, getLogger, friendly_auth_code, db_test_case_factory

logger = getLogger('users.db')

SQL_CREATE_TABLE_USERS = '''
-- Avoid clashing with 'user' builtin name
CREATE TABLE users
(
  id                    SERIAL PRIMARY KEY,
  -- Friendly ID for URL's and personal page
  id_hash               CHAR(8) UNIQUE,
  created               TIMESTAMP,
  first_name            VARCHAR(255),
  last_name             VARCHAR(255),
  email                 VARCHAR(255),
  telephone_mobile      VARCHAR(255),
  -- Auth token for authentication, take care not to expose it!
  auth_code             CHAR(12) UNIQUE
);

CREATE INDEX users_id_hash_index ON users(id_hash);

CREATE TABLE users_profilepic
(
  id                SERIAL PRIMARY KEY,
  user_id           INTEGER REFERENCES users(id),
  path              VARCHAR(255),
  created           TIMESTAMP,
  -- True if original, false if transcoded
  original          BOOLEAN,
  -- Resolution info in pixels
  width             SMALLINT,
  height            SMALLINT,
  -- Transcoder log
  log               TEXT
);

CREATE INDEX users_profilepic_user_id on users_profilepic(user_id);

CREATE TABLE users_bio
(
  id                SERIAL PRIMARY KEY,
  user_id           INTEGER REFERENCES users(id),
  created           TIMESTAMP,
  -- Short description like "paraglider pilot, I do the occasional hike", more strict length restriction should be
  -- applied on insertion
  subtitle          VARCHAR(255),
  -- Full bio text
  body              TEXT
);

CREATE INDEX users_bio_user_id on users_bio(user_id);
'''


class Db():
    @classmethod
    async def create(cls, existingconn=None):
        "Pass existingconn for unittesting"
        db = cls()
        db.conn = existingconn or await asyncpg.create_pool(dsn=environ["DB_URI_ATSITE"])
        return db

    async def create_tables(self):
        return await self.conn.execute(SQL_CREATE_TABLE_USERS)

    async def check_auth(self, auth_code):
        "Returns *False* if auth_code wrong, *user_id* if right, and *None* if user not found"
        out = False
        # Auth code is always uppercase
        user = await self.conn.fetchrow('SELECT id, auth_code FROM users WHERE auth_code=$1', auth_code.upper())
        if user:
            # Strip out any whitespace
            if auth_code.strip() == user['auth_code'].strip():
                out = user['id']
        else:
            out = None
        return out

    async def get_user_by_id(self, user_id):
        user = await self.conn.fetchrow('SELECT * FROM users WHERE id=$1', user_id)
        if not user:
            raise Exception("User with id %s does not exist", user_id)
        return await record_to_dict(user)

    async def getuser(self, id_hash, pass_auth_code=False, exclude_sensitive=False):
        "Get user in json format. Should never pass auth token, just for testing"
        user = await self.conn.fetchrow('SELECT * FROM users WHERE id_hash=$1', id_hash)
        if not user:
            return None
        # Take care to make it a tuple to prevent making a set of letters
        exclude = set(('auth_code',)) if not pass_auth_code else set()
        if exclude_sensitive:
            exclude = exclude.union(set(('email', 'telephone_mobile', 'id_hash', 'created', 'profilepic_original')))
        return await record_to_dict(user, exclude=exclude)

    async def getuser_id(self, id_hash):
        user_id = await self.conn.fetchval('SELECT id FROM users WHERE id_hash=$1', id_hash)
        return user_id

    async def getuser_hash(self, id):
        user_id_hash = await self.conn.fetchval('SELECT id_hash FROM users WHERE id=$1', id)
        return user_id_hash

    async def insertuser(self, userjson, id_hash=None, id_hash_collision_retry=False):
        "Make new user based on json representation"
        u = dict()
        created = userjson.get('created', datetime.datetime.now())
        # URL-friendly and incremented-db-id-confuscating alphanumeric string identifier
        u['id_hash'] = id_hash or await friendlyhash()
        # Use in e.g. telegram user linking
        u['auth_code'] = await friendly_auth_code()
        # Parse if ISO string time
        u['created'] = created if type(created) == datetime.datetime else dateutil.parser.parse(created)
        u['first_name'] = userjson.get('first_name')
        u['last_name'] = userjson.get('last_name')
        u['email'] = userjson['email']
        u['telephone_mobile'] = userjson.get('telephone_mobile')
        async def ins(u):
            return await conn.fetchval('''
            INSERT INTO users (id, id_hash, created, first_name, last_name, email, telephone_mobile, auth_code)
            VALUES (DEFAULT, $1, $2, $3, $4, $5, $6, $7) RETURNING id
            ''', u['id_hash'], u['created'], u['first_name'], u['last_name'], u['email'], u['telephone_mobile'], u['auth_code'])
        # We need to handle friendly hash collisions
        for i in range(100):
            if i == 99:
                raise Exception("Impossible!")
            try:
                # Use nested transaction such that only this block fails and we can still use conn
                async with self.conn.transaction():
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
                u = await db.getuser(fh, pass_auth_code=True, existingconn=conn)
                assert u['first_name'] == "Fonz"
                assert len(u['auth_code']) == 5
                u = await db.getuser(fh, existingconn=conn)
                assert u.get('auth_code', -1) == -1
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

    l = asyncio.get_event_loop()
    db = l.run_until_complete(Db.create())

    if args.create:
        l.run_until_complete(db.create_tables())
        logger.info("Created tables")

    if args.test or args.importusers:
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
            l.close()
        logger.info("Completed successfully")
