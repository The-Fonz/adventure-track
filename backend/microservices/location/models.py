from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, DateTime
from geoalchemy2 import Geometry

Base = declarative_base()


class GpsPoint(Base):
    "3D lat/lon/alt point"
    __tablename__ = 'gps_point'
    id = Column(Integer, primary_key=True)
    # All times in UTC please
    timestamp = Column(DateTime)
    # Standard WGS84 lat/lon
    # Have to use POINTZ here, not in geoalchemy2 docs
    # (dimension keyword does not work)
    geom = Column(Geometry(geometry_type='POINTZ', srid=4326))
    # Associate point with user, do not constrain as foreignkey as it
    # might be in a different microservice
    user_id = Column(Integer)
