import asyncio

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from aiohttp import web
import aiohttp_jinja2
import jinja2


async def site_factory(wampsess):
    """
    Creates aiohttp server listening on specified port
    :param wampsession:
    :return:
    """
    @aiohttp_jinja2.template('frontpage.html')
    async def frontpage(request):
        # name = request.match_info.get('name', 'Anonymous')
        msgs = await wampsess.call('com.messages.getall', 4, 5, 6)
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

    loop = asyncio.get_event_loop()

    await loop.create_server(app.make_handler(), '0.0.0.0', 5000)


class SiteComponent(ApplicationSession):
    def __init__(self, config=None):
        ApplicationSession.__init__(self, config)
        print("component created")

    def onConnect(self):
        print("transport connected")
        self.join(self.config.realm)

    def onChallenge(self, challenge):
        print("authentication challenge received")

    async def onJoin(self, details):
        print("session joined")

        await site_factory(self)

    def onLeave(self, details):
        print("session left")

    def onDisconnect(self):
        print("transport disconnected")


if __name__=="__main__":
    runner = ApplicationRunner(url="ws://localhost:8080/ws", realm="realm1")
    runner.run(SiteComponent)
