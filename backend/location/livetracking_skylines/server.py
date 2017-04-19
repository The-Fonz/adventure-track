import sys
import struct
from datetime import datetime, time, timedelta

from gevent.server import DatagramServer

# from sqlalchemy.exc import SQLAlchemyError
# from sqlalchemy.sql.expression import or_

# from skylines.database import db
# from skylines.model import User, TrackingFix, Follower, Elevation
# from skylines.sentry import sentry
from crc import check_crc, set_crc

import mock
User = mock.Mock()
TrackingFix = mock.Mock()
Elevation = mock.Mock()


import logging
logger = logging.getLogger('livetracking-skylines.server')

# More information about this protocol can be found in the XCSoar
# source code, source file src/Tracking/SkyLines/Protocol.hpp

MAGIC = 0x5df4b67b
TYPE_PING = 1
TYPE_ACK = 2
TYPE_FIX = 3
TYPE_TRAFFIC_REQUEST = 4
TYPE_TRAFFIC_RESPONSE = 5
TYPE_USER_NAME_REQUEST = 6
TYPE_USER_NAME_RESPONSE = 7

FLAG_ACK_BAD_KEY = 0x1

FLAG_LOCATION = 0x1
FLAG_TRACK = 0x2
FLAG_GROUND_SPEED = 0x4
FLAG_AIRSPEED = 0x8
FLAG_ALTITUDE = 0x10
FLAG_VARIO = 0x20
FLAG_ENL = 0x40

# for TYPE_TRAFFIC_REQUEST
TRAFFIC_FLAG_FOLLOWEES = 0x1
TRAFFIC_FLAG_CLUB = 0x2

USER_FLAG_NOT_FOUND = 0x1


def log(message):
    print message
    sys.stdout.flush()


class TrackingServer(DatagramServer):

    def ping_received(self, host, port, key, payload):
        if len(payload) != 8: return
        id, reserved, reserved2 = struct.unpack('!HHI', payload)

        flags = 0

        pilot = User.by_tracking_key(key)
        if not pilot:
            log("%s PING unknown pilot (key: %x)" % (host, key))
            flags |= FLAG_ACK_BAD_KEY
        else:
            log("%s PING %s -> PONG" % (host, unicode(pilot).encode('utf8', 'ignore')))

        data = struct.pack('!IHHQHHI', MAGIC, 0, TYPE_ACK, 0,
                           id, 0, flags)
        data = set_crc(data)
        self.socket.sendto(data, (host, port))

    def fix_received(self, host, key, payload):
        if len(payload) != 32: return

        pilot = User.by_tracking_key(key)
        if not pilot:
            log("%s FIX unknown pilot (key: %x)" % (host, key))
            return

        data = struct.unpack('!IIiiIHHHhhH', payload)

        fix = TrackingFix()
        fix.ip = host
        fix.pilot = pilot

        # import the time stamp from the packet if it's within a
        # certain range
        time_of_day_ms = data[1] % (24 * 3600 * 1000)
        time_of_day_s = time_of_day_ms / 1000
        time_of_day = time(time_of_day_s / 3600,
                           (time_of_day_s / 60) % 60,
                           time_of_day_s % 60,
                           (time_of_day_ms % 1000) * 1000)
        now = datetime.utcnow()
        now_s = ((now.hour * 60) + now.minute) * 60 + now.second
        if now_s - 1800 < time_of_day_s < now_s + 180:
            fix.time = datetime.combine(now.date(), time_of_day)
        elif now_s < 1800 and time_of_day_s > 23 * 3600:
            # midnight rollover occurred
            fix.time = (datetime.combine(now.date(), time_of_day) -
                        timedelta(days=1))
        else:
            log("bad time stamp: " + str(time_of_day))
            fix.time = datetime.utcnow()

        fix.time_visible = fix.time + timedelta(minutes=pilot.tracking_delay)

        flags = data[0]
        if flags & FLAG_LOCATION:
            latitude = data[2] / 1000000.
            longitude = data[3] / 1000000.
            fix.set_location(longitude, latitude)

            fix.elevation = Elevation.get(fix.location_wkt)

        if flags & FLAG_TRACK:
            fix.track = data[5]

        if flags & FLAG_GROUND_SPEED:
            fix.ground_speed = data[6] / 16.

        if flags & FLAG_AIRSPEED:
            fix.airspeed = data[7] / 16.

        if flags & FLAG_ALTITUDE:
            fix.altitude = data[8]

        if flags & FLAG_VARIO:
            fix.vario = data[9] / 256.

        if flags & FLAG_ENL:
            fix.engine_noise_level = data[10]

        log("{} FIX {} {} {}".format(
            host, unicode(pilot).encode('utf8', 'ignore'),
            fix.time and fix.time.time(), fix.location))

        # REMOVED: Commit fix to db logic

    # Removed:
    # - traffic_request_received
    # - username_request_received

    def __handle(self, data, (host, port)):
        if len(data) < 16: return

        header = struct.unpack('!IHHQ', data[:16])
        if header[0] != MAGIC: return
        if not check_crc(data): return

        with self.app.app_context():
            if header[2] == TYPE_FIX:
                self.fix_received(host, header[3], data[16:])
            elif header[2] == TYPE_PING:
                self.ping_received(host, port, header[3], data[16:])
            elif header[2] == TYPE_TRAFFIC_REQUEST:
                self.traffic_request_received(host, port, header[3], data[16:])
            elif header[2] == TYPE_USER_NAME_REQUEST:
                self.username_request_received(host, port, header[3], data[16:])

    def handle(self, data, address):
        try:
            self.__handle(data, address)
        except Exception:
            logger.exception()

    def serve_forever(self, **kwargs):
        super(TrackingServer, self).serve_forever(**kwargs)


if __name__=="__main__":
    print "Serving forever..."
    TrackingServer(':5597').serve_forever()
    print "Done..."
