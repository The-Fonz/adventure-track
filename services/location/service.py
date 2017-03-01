import pytest

from nameko.rpc import rpc
from nameko.testing.services import worker_factory
from nameko_sqlalchemy import Session
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from .models import Base, GpsPoint


class LocationService:
    name = "location_service"

    db = Session(Base)

    def add_point(self, user_id, timestamp, lon_lat_alt):
        "Add 3d point"
        ptstr = "SRID=4326;POINT({0:.6f} {1:.6f} {2:.6f})".format(*lon_lat_alt)
        p = GpsPoint(user_id=user_id, timestamp=timestamp, geom=ptstr)
        self.db.add(p)
        self.db.commit()

    @rpc
    def get_line(self, user_id, start=None, end=None, simplify=0):
        # Always filter by user ID
        # ST_Simplify only uses 2D points to simplify!
        # TODO: Select timestamps, points and manually convert these to json
        qs = ("SELECT ST_AsGeoJSON(ST_Simplify("
              "ST_MakeLine("
              "gps_point.geom ORDER BY gps_point.timestamp"
              "), :simplify, TRUE), :decimaldigits) "
              "FROM gps_point WHERE gps_point.user_id=:user_id ")
        # After start if given
        if start:
            qs += "AND gps_point.timestamp >= :start "
        if end:
            qs += "AND gps_point.timestamp <= :end "
        q = text(qs).bindparams(user_id=user_id,
                                simplify=simplify,
                                # Precision up to 0.11m
                                decimaldigits=6)
        return self.db.execute(q).first()[0]


@pytest.fixture
def session():
    "Create test db and session"
    import os
    engine = create_engine(os.environ['CA_PG_URI'])
    Base.metadata.create_all(engine)
    session_cls = sessionmaker(bind=engine)
    session = session_cls()
    yield session
    # Explicitly close db connection to avoid hang
    session.close()
    # Drop after testing finishes
    Base.metadata.drop_all(engine)


def test_service(session):
    import json
    from datetime import datetime, timedelta
    ls = worker_factory(LocationService, db=session)
    t = datetime.now()
    # Make test data, make sure they're not in line!
    for td,coords in zip([0,100,200], [(0,10,20),(3,4,5),(6,7,8)]):
        ls.add_point(1, t+timedelta(td), coords)
    # Get all points
    res = ls.get_line(1)
    res = json.loads(res)
    assert res["type"] == 'LineString'
    assert res["coordinates"] == [[0,10,20],[3,4,5],[6,7,8]]
    res = ls.get_line(1, simplify=10)
    res = json.loads(res)
    assert res["type"] == 'LineString'
    assert res["coordinates"] == [[0, 10, 20], [6, 7, 8]]
    # Get all points from time
    # Get all points until end
    # Get all points from start to end
    # Get simplified line
