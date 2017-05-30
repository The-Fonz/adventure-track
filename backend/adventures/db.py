import sys
import asyncio
import asyncpg
import unittest
import datetime
from os import environ

import jsonschema

from ..schemas import JSON_SCHEMA_LOCATION_GPS_POINT
from ..utils import db_test_case_factory, record_to_dict, records_to_dict, convert_to_datetime, getLogger, MicroserviceDb, friendlyhash

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
  description             TEXT,
  -- Friendly identifier for links
  url_hash                CHAR(8) UNIQUE,
  -- Specific tracking stuff or similar
  header_includes         TEXT
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


class Db(MicroserviceDb):

    async def create_tables(self):
        return await self.pool.execute(SQL_CREATE_TABLE_ADVENTURES)

    async def insert_adventure(self, adv):
        created = datetime.datetime.utcnow()
        url_hash = await friendlyhash()
        id = await self.pool.fetchval('''
        INSERT INTO adventures (id, name, created, start, stop, description, url_hash) VALUES (DEFAULT, $1, $2, $3, $4, $5, $6)
        RETURNING id;
        ''', adv['name'], created, adv.get('start'), adv.get('stop'), adv.get('description', None), url_hash)
        return id

    async def get_adventures(self, limit=100):
        "Get adventures sorted by creation datetime"
        recs = await self.pool.fetch('''
        SELECT * FROM adventures ORDER BY created LIMIT $1;
        ''', limit)
        return await records_to_dict(recs)

    async def get_adventure_by_id(self, adv_id):
        rec = await self.pool.fetchrow('SELECT * FROM adventures WHERE id = $1;', adv_id)
        return await record_to_dict(rec)

    async def get_adventure_by_hash(self, adv_hash):
        rec = await self.pool.fetchrow('SELECT * FROM adventures WHERE url_hash = $1;', adv_hash)
        if not rec:
            return None
        return await record_to_dict(rec)

    async def insert_adventure_user_link(self, link):
        id = await self.pool.fetchval('''
        INSERT INTO adventures_users_link (adventure_id, user_id, role) VALUES ($1, $2, $3) RETURNING id;
        ''', link['adventure_id'], link['user_id'], link.get('role', 'athlete'))
        return id

    async def get_adventure_user_link(self, link_id):
        rec = await self.pool.fetchrow('''SELECT * FROM adventures_users_link WHERE id = $1;''', link_id)
        return await record_to_dict(rec)

    async def get_adventure_user_links_by_user_id(self, user_id):
        recs = await self.pool.fetch('''SELECT * FROM adventures_users_link WHERE user_id=$1;''', user_id)
        if not recs:
            return None
        return await records_to_dict(recs)

    async def get_adventure_links(self, adv_id):
        recs = await self.pool.fetch('''SELECT * FROM adventures_users_link WHERE adventure_id = $1;''', adv_id)
        if not recs:
            return None
        return await records_to_dict(recs)


class AdventuresDbTestCase(db_test_case_factory(Db)):
    adv = {
        'name': 'TestAdventure',
        'description': 'Hi there!'
    }
    link = {
        'adventure_id': -1,
        'user_id': -100
    }
    def test_insert_and_retrieve(self):
        adv_id = self.lru(self.db.insert_adventure(self.adv))
        self.assertIsInstance(adv_id, int)
        adv_db = self.lru(self.db.get_adventure_by_id(adv_id))
        self.assertEqual(len(adv_db['url_hash']), 8)
        self.assertDictContainsSubset(self.adv, adv_db)
        # Can fail if someone else inserted adventure in the meantime, but very unlikely
        adv_recent = self.lru(self.db.get_adventures())[0]
        self.assertDictContainsSubset(self.adv, adv_recent)

    def test_link_fail(self):
        self.assertRaises(asyncpg.exceptions.ForeignKeyViolationError,
                          self.awrap(self.db.insert_adventure_user_link), self.link)

    def test_link(self):
        adv_id = self.lru(self.db.insert_adventure(self.adv))
        link = self.link.copy()
        link['adventure_id'] = adv_id
        link_id = self.lru(self.db.insert_adventure_user_link(link))
        self.assertIsInstance(link_id, int)
        link_retrieved = self.lru(self.db.get_adventure_user_link(link_id))
        # Test default
        self.assertEqual(link_retrieved['role'], 'athlete')
        # Test retrieving via adventure
        links = self.lru(self.db.get_adventure_links(adv_id))
        self.assertEqual(len(links), 1)


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
