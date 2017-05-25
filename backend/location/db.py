import sys
import asyncio
import asyncpg
import unittest
import datetime
from os import environ

import jsonschema

from ..schemas import JSON_SCHEMA_LOCATION_GPS_POINT
from ..utils import db_test_case_factory, records_to_dict, convert_to_datetime


SQL_CREATE_TABLE_GPS_POINT = '''
-- Enum for low space use
CREATE TYPE gps_point_source AS ENUM ('mobile', 'spot', 'telegram');

CREATE TABLE gps_point
(
  id                      SERIAL PRIMARY KEY,
  user_id                 INTEGER,
  source                  gps_point_source,
  -- Actual GPS timestamp
  timestamp               TIMESTAMP,
  -- When it was received by server
  received                TIMESTAMP,
  -- PostGIS geography type is lat/lon on the WGS84 spheroid
  -- It has less functionality and is slower in computations than geometry,
  -- but at least it's global so we don't have to mess with local projections
  ptz                     geography(POINTZ,4326),
  sog                     FLOAT,
  cog                     FLOAT
);
-- Fast joins
CREATE INDEX gps_point_user_id_index ON gps_point(user_id);
CREATE INDEX gps_point_timestamp_index on gps_point(timestamp);
-- Efficient index that only stores bbox of 128 rows by default
CREATE INDEX gps_point_ptz_index ON gps_point USING BRIN (ptz);
'''


class Db():
    @classmethod
    async def create(cls, existingconn=None):
        "Pass existingconn for unittesting"
        db = cls()
        db.conn = existingconn or await asyncpg.create_pool(dsn=environ["DB_URI_ATSITE"])
        return db

    async def create_tables(self):
        return await self.conn.execute(SQL_CREATE_TABLE_GPS_POINT)

    async def insert_gps_point(self, gps_point_dict, validate=True):
        # Don't mess with input data
        d = gps_point_dict.copy()
        # For convenience
        v = lambda n: d.get(n)
        # To string and later back to datetime.datetime so it can be validated
        d['received'] = datetime.datetime.utcnow().isoformat()
        if validate:
            # Throws ValidationError
            jsonschema.validate(d, JSON_SCHEMA_LOCATION_GPS_POINT)
        # Parse timestamps to datetime so asyncpg driver can handle them
        d['received'] = convert_to_datetime(v('received'))
        d['timestamp'] = convert_to_datetime(v('timestamp'))

        # Six decimal digits for about 1/9m precision
        pt_wkt = "SRID=4326;POINTZ({longitude:.6f} {latitude:.6f} {height_m_msl:.2f})".format(**v('ptz'))

        id = await self.conn.fetchval('''
        INSERT INTO gps_point (id, user_id, timestamp, received, ptz, sog, cog, source)
        VALUES (DEFAULT, $1, $2, $3, ST_GeogFromText($4), $5, $6, $7)
        RETURNING id;''', v('user_id'), v('timestamp'), v('received'), pt_wkt,
                                      v('speed_over_ground_kmh'), v('course_over_ground_deg'), v('source'))
        return id

    async def get_gps_points(self, user_id, return_vanilla=False, start=datetime.datetime.min, end=datetime.datetime.max):
        """
        Get GPS points of specific user.
        :param user_id: ID of user to query points for
        :param return_vanilla: Return in schema format, if False return frontend format, default False
        :param start:
        :param end:
        :return: 
        """
        recs = await self.conn.fetch('''
        SELECT user_id, timestamp, received, ST_AsText(ptz) ptz
        FROM gps_point
        WHERE user_id=$1 AND gps_point.timestamp >= $2 AND gps_point.timestamp <= $3
        ORDER BY gps_point.timestamp ASC;
        ''', user_id, start, end)
        # Return None if no results
        if not recs:
            return None
        # Same format as incoming
        if return_vanilla:
            return await records_to_dict(recs)
        # Convert to custom, efficient db format
        parsept = lambda p: [float(c) for c in p.split('(')[-1].split(')')[0].split()]
        return {"coordinates": [parsept(r['ptz']) for r in recs],
                "timestamps": [r['timestamp'].isoformat() for r in recs]}


class SomeTestCase(db_test_case_factory(Db)):
    def test_invalidpt(self):
        invalidpt = {
            "user_id": None,
        }
        # Should not validate
        self.assertRaisesRegex(jsonschema.exceptions.ValidationError,
                               "None is not of type 'integer'",
                               self.awrap(self.db.insert_gps_point),
                               invalidpt)

    def test_validpt(self):
        t = datetime.datetime.utcnow().isoformat()
        validpt = {
            "user_id": -10,
            "timestamp": t,
            "ptz": {
                "longitude": 5,
                "latitude": 6,
                "height_m_msl": 900
            }
        }
        id = self.lru(self.db.insert_gps_point(validpt))
        self.assertIsInstance(id, int)
        validpts_retrieved = self.lru(self.db.get_gps_points(-10, return_vanilla=True))
        # This key added when inserting
        del validpts_retrieved[0]['received']
        self.assertEqual(validpt, validpts_retrieved[0])
        validpts_retrieved_f = self.lru(self.db.get_gps_points(-10))
        self.assertEqual(validpts_retrieved_f, {"coordinates": [[5,6,900]], "timestamps": [t]})



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
