import signal
import asyncio
import logging

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from autobahn.wamp.exception import ApplicationError
from aiohttp import web
import aiohttp_jinja2
import jinja2


logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)7s: %(message)s'
)
logger = logging.getLogger('')


async def site_factory(wampsess):
    """
    Creates aiohttp server listening on specified port
    :param wampsession:
    :return:
    """
    @aiohttp_jinja2.template('frontpage.html')
    async def frontpage(request):
        # name = request.match_info.get('name', 'Anonymous')
        try:
            msgs = await wampsess.call('com.messages.fetchmsgs', 0)
        except ApplicationError:
            msgs = 'error'
            # Automatically prints exception information
            logger.exception("Could not reach com.messages.fetchmsgs")
        return {
            'adventures': [{}, {}, {}],
            'messages': msgs
        }

    @aiohttp_jinja2.template('trackuser.html')
    async def trackuser(request):
        hexslug = request.match_info.get('hexslug')
        return {'user': 'hithere ' + hexslug}

    app = web.Application()

    aiohttp_jinja2.setup(app, loader=jinja2.PackageLoader('backend.site'))

    app.router.add_get('/', frontpage)
    app.router.add_get(r'/u/{hexslug}', trackuser)

    # TODO: Use nginx instead
    import os.path as p
    # Assume working dir is repo root
    app.router.add_static('/static', p.abspath(p.join('client', 'static')))

    loop = asyncio.get_event_loop()

    await loop.create_server(app.make_handler(), '0.0.0.0', 5000)


class SiteComponent(ApplicationSession):
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

        await site_factory(self)

    # def onLeave(self, details):
    #     print("session left")
    #
    # def onDisconnect(self):
    #     print("transport disconnected")


if __name__=="__main__":

    l = asyncio.get_event_loop()

    runner = ApplicationRunner(url="ws://localhost:8080/ws", realm="realm1")
    # ApplicationRunner starts asyncio loop, and adds SIGTERM handler
    # Takes standard event loop
    protocol = runner.run(SiteComponent, start_loop=False)

    l.add_signal_handler(signal.SIGINT, l.stop)
    l.add_signal_handler(signal.SIGTERM, l.stop)

    l.run_forever()
    logger.info("Loop stopped")

    # Clean up stuff after loop stops
    # if protocol._session:
    #     print("Running protocol session leave")
    #     l.run_until_complete(protocol._session.leave())

    l.run_until_complete(l.shutdown_asyncgens())
    l.close()
    logger.info("Loop closed")
