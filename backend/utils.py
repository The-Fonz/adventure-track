import os
import re
import uuid
import json
import signal
import asyncio
import asyncpg
import logging
import datetime
import unittest

import dateutil.parser
from hashids import Hashids
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner


def getLogger(name):
    "Logging setup is done in __init__"
    return logging.getLogger(name)

logger = getLogger('utils')

def convert_to_datetime(s):
    """
    Converts an ISO string to datetime, but not if it's already a datetime obj.
    :param s: String or datetime.datetime
    :return: datetime.datetime
    """
    return s if isinstance(s, datetime.datetime) else dateutil.parser.parse(s)


def ptz_wkt_to_dict(ptz_wkt):
    "Parses well-known text representation of POINTZ to custom dict"
    m = re.search("\(([\d\.]+)\s*([\d\.]+)\s*([\d\.]+)\)", ptz_wkt)
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


async def friendlyhash():
    "Generate random hash of length 8"
    h = Hashids(salt=str(uuid.uuid4()), min_length=8)
    # Just to make sure that it's length 8, should always be the case anyway
    return h.encode(123)[:8]


async def friendly_auth_code():
    "Generate friendly uppercase code of length 5"
    h = Hashids(salt=str(uuid.uuid4()), min_length=5, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    return h.encode(456)[:5]


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
        asyncio.get_event_loop().stop()

    @classmethod
    def run_forever(cls):
        """
        Convenience method to avoid repetition.
        Pass a stopcallback to finish work or queues, gets called just before loop is closed,
        with protocol as single argument.
        """
        l = asyncio.get_event_loop()

        runner = ApplicationRunner(url="ws://localhost:8080/ws", realm="realm1")

        protocol = runner.run(cls, start_loop=False)

        l.add_signal_handler(signal.SIGINT, l.stop)
        l.add_signal_handler(signal.SIGTERM, l.stop)

        l.run_forever()
        logger.info("Loop stopped")

        # Must prevent a default as 3rd argument to avoid AttributeError
        if getattr(protocol, '_session', None) and getattr(protocol._session, 'cleanup', None):
            logger.info("Running cleanup method...")
            l.run_until_complete(protocol._session.cleanup(l))

        l.close()
        logger.info("Loop closed")


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