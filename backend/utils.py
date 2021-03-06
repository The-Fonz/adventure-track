import os
import re
import sys
import uuid
import json
import signal
import asyncio
import asyncpg
import logging
import datetime
import unittest
import pytz

import dateutil.parser
from hashids import Hashids
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner


def getLogger(name):
    "Logging setup is done in __init__"
    return logging.getLogger(name)

logger = getLogger('utils')


def localtime_to_utc(dt, remove_tzinfo=False):
    "Converts naive datetime.datetime object from local timezone to UTC"
    # Assumes that naive datetime object is in local tz (see docs)
    # Will also work correctly if it already has tz information
    dt = dt.astimezone(pytz.utc)
    # For asyncpg compatibility
    if remove_tzinfo:
        dt = dt.replace(tzinfo=None)
    return dt


def convert_to_datetime(s):
    """
    Converts an ISO string to datetime, but not if it's already a datetime obj. None stays None.
    :param s: String or datetime.datetime
    :return: datetime.datetime
    """
    if s == None:
        return None
    else:
        return s if isinstance(s, datetime.datetime) else dateutil.parser.parse(s)


def ptz_wkt_to_dict(ptz_wkt):
    "Parses well-known text representation of POINTZ to custom dict"
    m = re.search("\(([\-\d\.]+)\s*([\-\d\.]+)\s*([\-\d\.]+)\)", ptz_wkt)
    if not m:
        raise Exception("Format not recognized: %s", ptz_wkt)
    return {
        "longitude": float(m.group(1)),
        "latitude": float(m.group(2)),
        "height_m_msl": float(m.group(3))
    }


async def record_to_dict(record, exclude=set(), parse_media=True, parse_ptz=True):
    "Transform record to json, exclude keys if needed"
    out = {}
    for k,v in record.items():
        # Parse media if not None
        if k == 'media' and parse_media and v:
            ml = json.loads(v)
            mo = dict()
            for m in ml:
                typ = m['type']
                if not mo.get(typ):
                    mo[typ] = dict()
                # {<media_type>: {<conf_name>: {...}}, ...}
                conf_name = m['conf_name']
                # Exclude None config names
                if conf_name:
                    # Exclude sensitive keys in media dict as well
                    mo[typ][conf_name] = {k:v for k,v in m.items() if k not in exclude}
            out[k] = mo
        elif parse_ptz and k == 'ptz':
            # Convert WKT to custom dict
            out[k] = ptz_wkt_to_dict(v)
        elif k not in exclude:
            # Parse json
            if type(v) == str and v.strip().startswith('{'):
                v = json.loads(v)
            # Json parser cannot serialize datetime by default
            elif type(v) == datetime.datetime:
                v = v.isoformat()
            out[k] = v
    return out

async def records_to_dict(records, **kwargs):
    "Converts list of asyncpg.Record to json"
    out = []
    # Can make async using await asyncio.sleep(0) but should be real fast
    for r in records:
        out.append(await record_to_dict(r, **kwargs))
    return out


async def friendlyhash(length=8):
    "Generate random hash"
    h = Hashids(salt=str(uuid.uuid4()), min_length=length)
    # Just to make sure that it's length 8, should always be the case anyway
    return h.encode(123)[:length]


async def friendly_auth_code(length=12):
    "Generate friendly uppercase code"
    h = Hashids(salt=str(uuid.uuid4()), min_length=length, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    return h.encode(456)[:length]


class BackendAppSession(ApplicationSession):
    def __init__(self, config=None):
        ApplicationSession.__init__(self, config)
        logger.info("component created")

    def onConnect(self):
        logger.info("transport connected")
        self.join(self.config.realm, [u"ticket"], 'backend')

    def onChallenge(self, challenge):
        logger.info("authentication challenge received")
        if challenge.method == u"ticket":
            return os.environ['AT_CROSSBAR_TICKET']
        else:
            raise Exception("Invalid auth method %s", challenge.method)

    # def onLeave(self, details):
    #     print("session left")
    #
    def onDisconnect(self):
        "Override this class when implementing custom cleanup logic"
        logger.warning("transport disconnected, stopping event loop...")
        # TODO: Clean disconnect using .leave (gave some txaio error though)
        # Handle cleanup methods here if possible
        if getattr(self, 'cleanup', None):
            logger.info("Running cleanup method...")
            l = asyncio.get_event_loop()
            l.run_until_complete(self.cleanup(l))
        asyncio.get_event_loop().stop()

    @classmethod
    def run_forever(cls, loop=None):
        """
        Convenience method to avoid repetition.
        Pass a stopcallback to finish work or queues, gets called just before loop is closed,
        with protocol as single argument.
        """
        if not loop:
            l = asyncio.get_event_loop()
        else:
            l = loop

        runner = ApplicationRunner(url="ws://localhost:8080/ws", realm="realm1")

        # .run() returns a coro that creates connection
        protocol = l.run_until_complete(runner.run(cls, start_loop=False))

        l.add_signal_handler(signal.SIGINT, l.stop)
        l.add_signal_handler(signal.SIGTERM, l.stop)

        l.run_forever()

        logger.info("Loop stopped")

        # Must prevent a default as 3rd argument to avoid AttributeError
        if getattr(protocol, '_session', None) and getattr(protocol._session, 'cleanup', None):
            logger.info("Running cleanup method...")
            l.run_until_complete(protocol._session.cleanup(l))

        l.close()
        logger.info("Loop closed, hard exit...")
        sys.exit()


class MicroserviceDb():
    "Inherit from this class to create service Db"
    @classmethod
    async def create(cls, existingconn=None):
        "Pass existingconn for unittesting"
        db = cls()
        db.pool = existingconn or await asyncpg.create_pool(dsn=os.environ["DB_URI_ATSITE"])
        return db


def db_test_case_factory(db_cls):
    """
    Use this to create TestCase class with proper db.
    Subclass this like `class SomeTestCase(db_test_case_factory(db)): ...`
    """
    class DbTestCase(unittest.TestCase):
        "Use self.lru for run_until_complete, self.db for db access"
        def setUp(self):
            self.l = asyncio.get_event_loop()
            # Easy access
            self.lru = self.l.run_until_complete
            self.conn = self.lru(asyncpg.connect(dsn=os.environ["DB_URI_ATSITE"]))
            self.t = self.conn.transaction()
            self.lru(self.t.start())
            self.db = self.lru(db_cls.create(existingconn=self.conn))
            def raisesWrapper(coro_func):
                "Closure to make it possible to pass coro to assertRaises"
                def f(*args, **kwargs):
                    coro = coro_func(*args, **kwargs)
                    return self.lru(coro)
                return f
            self.awrap = raisesWrapper

        def tearDown(self):
            # Roll back transaction, close connection
            self.lru(self.t.rollback())
            self.lru(self.conn.close())

    return DbTestCase