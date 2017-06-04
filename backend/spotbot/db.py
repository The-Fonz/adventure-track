import sys
import json
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

-- History of messages so we can figure out which one we received
CREATE TABLE spotbot_msgs
(
  -- Own unique ID
  id                      SERIAL PRIMARY KEY,
  -- Received
  created                 TIMESTAMP,
  -- Timestamp of message
  timestamp               TIMESTAMP,
  -- ID of our user
  user_id                 INTEGER,
  -- ID of msg given by SPOT
  spot_msg_id             INTEGER,
  spot_msg_type           VARCHAR(255),
  spot_msg_latitude       FLOAT,
  spot_msg_longitude      FLOAT,
  spot_msg_altitude       FLOAT,
  spot_msg_battery_state  VARCHAR(255),
  -- Original message
  spot_msg                     JSONB
);

CREATE INDEX spotbot_msgs_user_id ON spotbot_msgs(user_id);
CREATE INDEX spotbot_msgs_spot_msg_id ON spotbot_msgs(spot_msg_id);
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
        created = datetime.datetime.utcnow()
        # Init to long time ago, so we can just compare and forget about the None checks
        last_queried = datetime.datetime.min
        l = lambda n: linkdict.get(n)
        id = await self.conn.fetchval('''
        INSERT INTO spotbot_link (id, user_id, feed_id, created, last_queried)
        VALUES (DEFAULT, $1, $2, $3, $4) RETURNING id;
        ''', l('user_id'), l('feed_id'), created, last_queried)
        return id

    async def get_all_links(self, raw=False):
        recs = await self.conn.fetch('''
        SELECT * FROM spotbot_link;
        ''')
        if raw:
            return recs
        return await records_to_dict(recs)

    async def update_link_last_queried(self, link_id):
        now = datetime.datetime.utcnow()
        await self.conn.execute('''
        UPDATE spotbot_link SET last_queried = $2
        WHERE id = $1;
        ''', link_id, now)

    async def insert_msg(self, msg):
        now = datetime.datetime.utcnow()
        id = await self.conn.fetchval('''
        INSERT INTO spotbot_msgs (id, created, timestamp, user_id, spot_msg_id, spot_msg,
        spot_msg_type, spot_msg_latitude, spot_msg_longitude, spot_msg_altitude, spot_msg_battery_state)
        VALUES (DEFAULT, $1, $2, $3, $4, $5, $6, $7, $8, $9, $10);
        ''', now, msg['timestamp'], msg['user_id'], msg['spot_msg_id'], json.dumps(msg['spot_msg']),
        msg['spot_msg_type'], msg['spot_msg_latitude'], msg['spot_msg_longitude'], msg['spot_msg_altitude'],
                                      msg['spot_msg_battery_state'])
        return id

    async def spot_msg_id_exists(self, user_id, spot_msg_id):
        "Returns true if msg id exists, false otherwise"
        # spot_msg_id is probably globally unique, but query for user_id too just in case
        # This also allows multiple accounts to use the same spot device, however useful that may be...
        id = await self.conn.fetchval('''
        SELECT id FROM spotbot_msgs WHERE user_id = $1 AND spot_msg_id = $2; 
        ''', user_id, spot_msg_id)
        if id: return True
        else: return False

    async def get_spot_msgs_by_user_id(self, user_id, limit=50):
        recs = await self.conn.fetch('''
        SELECT * FROM spotbot_msgs WHERE user_id = $1 ORDER BY timestamp DESC LIMIT $2;
        ''', user_id, limit)
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
