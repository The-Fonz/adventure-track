import pytest

from nameko.rpc import rpc
from nameko.testing.services import worker_factory
from nameko_sqlalchemy import Session
from sqlalchemy import text

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
    def get_points(self, user_id, start=None, end=None):
        # Always filter by user ID
        # ST_Simplify only uses 2D points to simplify!
        qs = ("SELECT gps_point.timestamp, ST_AsText(gps_point.geom) "
              "FROM gps_point WHERE gps_point.user_id=:user_id ")
        paramkwargs = {'user_id': user_id}
        # After start if given
        if start:
            qs += "AND gps_point.timestamp >= :start "
            paramkwargs['start'] = start
        if end:
            qs += "AND gps_point.timestamp <= :end "
            paramkwargs['end'] = end
        qs += "ORDER BY gps_point.timestamp ASC "
        q = text(qs).bindparams(**paramkwargs)
        res = self.db.execute(q).fetchall()
        # Convert to custom format
        parsept = lambda p: [float(c) for c in p.split('(')[-1].split(')')[0].split()]
        return {"coordinates": [parsept(p) for d,p in res],
                "timestamps": [d.isoformat() for d,p in res]}


@pytest.mark.parametrize('base', [Base])
def test_service(testsession):
    from datetime import datetime, timedelta
    ls = worker_factory(LocationService, db=testsession)
    t = datetime.now()
    # Make test data, make sure they're not in line!
    for td,coords in zip([0,100,200], [(0,10,20),(3,4,5),(6,7,8)]):
        ls.add_point(1, t+timedelta(td), coords)
    # Get all points
    res = ls.get_points(1)
    assert res["coordinates"] == [[0.,10.,20.],[3.,4.,5.],[6.,7.,8.]]
    # Check timestamp format
    assert res["timestamps"][0] == t.isoformat()
    # Get all points except first
    res = ls.get_points(1, start=t+timedelta(1))
    assert res["coordinates"] == [[3., 4., 5.], [6., 7., 8.]]
    # Get only middle point
    res = ls.get_points(1, start=t + timedelta(1), end=t + timedelta(150))
    assert res["coordinates"] == [[3.,4.,5.]]
