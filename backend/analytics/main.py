import signal
import asyncio

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from aiohttp import web
import aiohttp_jinja2
import jinja2

from .db import Db
from ..utils import getLogger

logger = getLogger('analytics.main')


async def site_factory(wampsess):
    """
    Creates aiohttp server listening on specified port
    :param wampsession:
    :return:
    """
    @aiohttp_jinja2.template('dashboard.html')
    async def dashboard(request):
        # name = request.match_info.get('name', 'Anonymous')
        # try:
        #     # Get n most recent messages, unique by user
        #     msgs = await wampsess.call('at.messages.uniquemsgs', n=5)
        # except ApplicationError:
        #     msgs = 'error'
        #     # Automatically prints exception information
        #     logger.exception("Could not reach at.messages.fetchmsgs")
        return {}

    app = web.Application()

    aiohttp_jinja2.setup(app, loader=jinja2.PackageLoader('backend.analytics'))

    app.router.add_get('/', dashboard)

    loop = asyncio.get_event_loop()

    await loop.create_server(app.make_handler(), '127.0.0.1', 5001)


class AnalyticsComponent(ApplicationSession):
    def __init__(self, config=None):
        ApplicationSession.__init__(self, config)
        logger.info("component created")

    def onConnect(self):
        logger.info("transport connected")
        self.join(self.config.realm)

    def onChallenge(self, challenge):
        logger.info("authentication challenge received")

    async def onJoin(self, details):
        logger.info("session joined")

        self.db = await Db.create()

        async def insert_event(evt):
            "For internal services"
            await self.db.insert_event(evt)

        self.register(insert_event, 'at.analytics.insert_event')

        async def log_analytics_event_fromwamp(details, evt):
            "Event logging for browser. Returns True if succeeded"
            try:
                session = await self.call('wamp.session.get', details.caller)
                peer = session['transport']['peer']
                # TODO: Create event
                await log_analytics_event(evt)
                return True
            except Exception:
                logger.exception("Something went wrong when trying to construct or log analytics event")
                return False

        self.register(log_analytics_event_fromwamp, 'at.site.log_analytics_event_fromwamp',
                      RegisterOptions(details_arg='details'))

        await site_factory(self)

    # def onLeave(self, details):
    #     print("session left")
    #
    def onDisconnect(self):
        logger.warn("transport disconnected, stopping event loop...")
        asyncio.get_event_loop().stop()


if __name__=="__main__":

    l = asyncio.get_event_loop()

    runner = ApplicationRunner(url="ws://localhost:8080/ws", realm="realm1")

    protocol = runner.run(AnalyticsComponent, start_loop=False)

    l.add_signal_handler(signal.SIGINT, l.stop)
    l.add_signal_handler(signal.SIGTERM, l.stop)

    l.run_forever()
    logger.info("Loop stopped")

    # Clean up stuff after loop stops
    # if protocol._session:
    #     print("Running protocol session leave")
    #     l.run_until_complete(protocol._session.leave())

    l.close()
    logger.info("Loop closed")
