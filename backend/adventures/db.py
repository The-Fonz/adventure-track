import sys
import asyncio
import asyncpg
import unittest
import datetime
from os import environ

import jsonschema

from ..schemas import JSON_SCHEMA_LOCATION_GPS_POINT
from ..utils import db_test_case_factory, records_to_dict, convert_to_datetime, getLogger

logger = getLogger('adventures.db')


SQL_CREATE_TABLE_ADVENTURES = '''
CREATE TABLE adventures
(
  id                      SERIAL PRIMARY KEY,
  name                    VARCHAR(255),
  created                 TIMESTAMP,
  -- User position/content will be visible after start, until stop
  start                   TIMESTAMP,
  -- Null if open-ended
  stop                    TIMESTAMP,
  description             TEXT
);

CREATE TYPE user_adventure_role AS ENUM ('athlete', 'content_creator'); 

CREATE TABLE adventures_users_link
(
  id                      SERIAL PRIMARY KEY,
  adventure_id            INTEGER REFERENCES adventures(id),
  -- Is owned by other microservice so no db constraint
  user_id                 INTEGER,
  role                    user_adventure_role
);

-- Fast joins
CREATE INDEX adventures_users_link_adventure_id_index ON adventures_users_link(adventure_id);
CREATE INDEX adventures_users_link_user_id_index ON adventures_users_link(user_id);
'''


class Db():
    @classmethod
    async def create(cls, existingconn=None):
        "Pass existingconn for unittesting"
        db = cls()
        db.conn = existingconn or await asyncpg.create_pool(dsn=environ["DB_URI_ATSITE"])
        return db

    async def create_tables(self):
        return await self.conn.execute(SQL_CREATE_TABLE_ADVENTURES)

    async def insert_adventure(self):
        pass


class AdventuresDbTestCase(db_test_case_factory(Db)):
    def test_invalidpt(self):
        pass


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
