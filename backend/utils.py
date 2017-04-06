import json
import uuid
import logging
import datetime

from hashids import Hashids


def getLogger(name):
    "Centralized logging setup"
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)7s: %(asctime)s %(name)s:%(lineno)s %(message)s'
    )
    return logging.getLogger(name)


async def record_to_json(record):
    out = {}
    for k,v in record.items():
        # Parse json
        if type(v) == str and v.strip().startswith('{'):
            v = json.loads(v)
        # Json parser cannot serialize datetime by default
        elif type(v) == datetime.datetime:
            v = v.isoformat()
        out[k] = v
    return out

async def records_to_json(records):
    "Converts list of asyncpg.Record to json"
    out = []
    # Can make async using await asyncio.sleep(0) but should be real fast
    for r in records:
        out.append(await record_to_json(r))
    return out


async def friendlyhash():
    "Generate random hash of length 8"
    h = Hashids(salt=str(uuid.uuid4()), min_length=8)
    # Just to make sure that it's length 8, should always be the case anyway
    return h.encode(123)[:8]