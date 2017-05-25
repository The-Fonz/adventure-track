import logging
import asyncio
from os import environ
import datetime

import asyncpg
from ..utils import record_to_dict, records_to_dict

logger = logging.getLogger('analytics.db')


SQL_CREATE_TABLE_ANALYTICS_EVENTS = """
CREATE TABLE analytics_events
(
    id SERIAL PRIMARY KEY,
    received TIMESTAMP,

    event_type VARCHAR(255),
    user_id VARCHAR(255),
    browser_id VARCHAR(255),

    request_url VARCHAR(2048),
    request_ip INET,
    request_method VARCHAR(255),
    request_referer VARCHAR(2048),
    request_user_agent VARCHAR(2048),

    response_status INTEGER,
    response_length INTEGER,
    response_time_taken FLOAT,

    extra JSONB
);
CREATE INDEX analytics_events_event_type_index ON analytics_events (event_type);
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

    async def get_daily_visitors(self, existingconn=None):
        "Return (<dates_array>, <total_pageviews_array>, <unique_visitor_count>)"
        # Pool has same interface as connection
        conn = existingconn or self.pool
        total_pageviews = await conn.fetch(
            "SELECT date_trunc('day', received) as dt, count(received) "
            "FROM analytics_events "
            "WHERE event_type = 'pageview' GROUP BY dt ORDER BY dt ASC;"
        )
        unique_visitors = await conn.fetch(
            "SELECT a2.dt, count(a2.bid) FROM (SELECT DISTINCT ON (dt, a.browser_id) date_trunc('day', a.received) as dt, browser_id as bid FROM analytics_events as a WHERE a.event_type = 'pageview') as a2 GROUP BY a2.dt ORDER BY dt ASC;"
        )
        return [
            [rec['dt'] for rec in total_pageviews],
            [rec['count'] for rec in total_pageviews],
            [rec['count'] for rec in unique_visitors]
        ]

    async def insert_event(self, evt, existingconn=None):
        """
        Inserts event list into db.
        Using a list for easy insertion. (It ain't pretty but saves some code.)
        """
        conn = existingconn or await self.pool.acquire()
        received = datetime.datetime.utcnow()
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
