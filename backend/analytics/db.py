import logging
import asyncio
from os import environ
import datetime

import asyncpg
from ..utils import record_to_json, records_to_json

logger = logging.getLogger('analytics.db')


SQL_CREATE_TABLE_ANALYTICS_EVENTS = """
CREATE TABLE analytics_events
(
    id SERIAL PRIMARY KEY,
    received TIMESTAMP,

    event_type TEXT,
    user_id TEXT,
    browser_id TEXT,

    request_url TEXT,
    request_ip INET,
    request_method TEXT,
    request_referer TEXT,
    request_user_agent TEXT,

    response_status INTEGER,
    response_length INTEGER,
    response_time_taken FLOAT,

    extra JSONB
);
"""


class Db():
    @classmethod
    async def create(cls, loop=None, num_video_queues=2):
        "Use like `await Db.create()` to enable use of async methods"
        db = Db()
        db.pool = await asyncpg.create_pool(dsn=environ["DB_URI_ATSITE"])
        return db

    async def create_tables(self, existingconn=None):
        conn = existingconn or await self.pool.acquire()
        stat = await conn.execute(SQL_CREATE_TABLE_ANALYTICS_EVENTS)
        if not existingconn:
            await self.pool.release(conn)
        return stat

    async def insert_event(self, evt, existingconn=None):
        """
        Inserts event list into db.
        Using a list for easy insertion. (It ain't pretty but saves some code.)
        """
        conn = existingconn or await self.pool.acquire()
        received = datetime.datetime.now()
        id = await conn.fetchval(
            "INSERT INTO analytics_events "
            "(received, event_type, user_id, browser_id, request_url, request_ip, request_method, request_referer, request_user_agent, response_status, response_length, response_time_taken, extra) "
            "VALUES "
            "($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12, $13) "
            "RETURNING id;",
            received, *evt)
        if not existingconn:
            await self.pool.release(conn)


if __name__=="__main__":
    # Nice output when run on cmdline
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

    loop = asyncio.get_event_loop()
    # loop.set_debug(True)

    if args.create:
        db = loop.run_until_complete(Db.create())
        stat = loop.run_until_complete(db.create_tables())
        logger.info("Created tables, status: %s", stat)
