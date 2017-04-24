import sys
import asyncio
import asyncpg
import unittest
import datetime
from os import environ

from ..utils import records_to_dict


SQL_CREATE_TABLE_SPOTBOT_LINK = '''
CREATE TABLE spotbot_link
(
  id                      SERIAL PRIMARY KEY,
  user_id                 INTEGER NOT NULL,
  feed_id                 VARCHAR(255) NOT NULL,
  created                 TIMESTAMP,
  last_queried            TIMESTAMP
);
-- Fast joins
CREATE INDEX spotbot_link_user_id ON spotbot_link(user_id);
CREATE INDEX spotbot_link_feed_id ON spotbot_link(feed_id);
'''


class Db():
    @classmethod
    async def create(cls, existingconn=None):
        "Pass existingconn for unittesting"
        db = cls()
        db.conn = existingconn or await asyncpg.create_pool(dsn=environ["DB_URI_ATSITE"])
        return db

    async def create_tables(self):
        return await self.conn.execute(SQL_CREATE_TABLE_SPOTBOT_LINK)

    async def create_link(self, linkdict):
        created = datetime.datetime.now()
        # Init to long time ago, so we can just compare and forget about the None checks
        last_queried = datetime.datetime.min
        l = lambda n: linkdict.get(n)
        id = self.conn.fetchval('''
        INSERT INTO spotbot_link (id, user_id, feed_id, created, last_queried)
        VALUES (DEFAULT, $1, $2, $3, $4) RETURNING id;
        ''', l('user_id'), l('feed_id'), created, last_queried)
        return id

    async def get_all_links(self, raw=False):
        recs = self.conn.fetchrows('''
        SELECT * FROM spotbot_link; 
        ''')
        if raw:
            return recs
        return await records_to_dict(recs)


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--create', action='store_true',
                        help="Create db tables and indexes")
    parser.add_argument('--test', action='store_true',
                        help="Test db")
    args = parser.parse_args()

    if args.create:
        l = asyncio.get_event_loop()
        db = l.run_until_complete(Db.create())
        l.run_until_complete(db.create_tables())

    if args.test:
        # Pass only system name, ignore other args
        unittest.main(verbosity=1, argv=sys.argv[:1])
