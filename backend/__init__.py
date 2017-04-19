#
# Centralized logging setup
#

import os
import logging

from .utils import getLogger
l = getLogger('backend')

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s][%(levelname)s] %(name)s '
           '%(filename)s:%(funcName)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

sentry_dsn = os.environ.get('AT_SENTRY_DSN')
if sentry_dsn:
    from raven import Client
    from raven.handlers.logging import SentryHandler
    from raven.conf import setup_logging

    client = Client(sentry_dsn)
    handler = SentryHandler(client, level='WARNING')
    setup_logging(handler)
    l.info("Set up Sentry client")
