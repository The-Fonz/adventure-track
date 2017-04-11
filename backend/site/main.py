import signal
import asyncio
import datetime
from time import time
import uuid

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from autobahn.wamp.exception import ApplicationError, TransportLost
from autobahn.wamp.types import RegisterOptions
from aiohttp import web
import aiohttp_jinja2
import jinja2

from ..utils import getLogger

logger = getLogger('site.main')


def errpage(request, status_text, status_code):
    "Returns custom error page"
    context = {'status_text': status_text, 'status_code': status_code}
    return aiohttp_jinja2.render_template('errpage.html', request, context)


async def site_factory(wampsess, middlewares):
    """
    Creates aiohttp server listening on specified port
    :param wampsession:
    :return:
    """
    @aiohttp_jinja2.template('frontpage.html')
    async def frontpage(request):
        # name = request.match_info.get('name', 'Anonymous')
        try:
            # Get n most recent messages, unique by user
            msgs = await wampsess.call('at.messages.uniquemsgs', n=5)
        except ApplicationError:
            msgs = 'error'
            # Automatically prints exception information
            logger.exception("Could not reach at.messages.fetchmsgs")
        return {
            'adventures': [],
            'messages': msgs
        }

    async def trackuser(request):
        user_id_hash = request.match_info.get('user_id_hash')
        try:
            user = await wampsess.call('at.users.get_user_by_hash', user_id_hash)
            if not user:
                # Proper escaping done in template
                return errpage(request, "User {} does not exist".format(user_id_hash), 404)
        except ApplicationError:
            logger.exception("Could not reach at.users.get_user_by_hash")
            return errpage(request, "Could not reach user service", 500)
        context = {'user': user}
        response = aiohttp_jinja2.render_template('trackuser.html', request, context)
        return response

    app = web.Application(middlewares=middlewares)

    aiohttp_jinja2.setup(app, loader=jinja2.PackageLoader('backend.site'))

    app.router.add_get('/', frontpage)
    app.router.add_get(r'/u/{user_id_hash}', trackuser)

    loop = asyncio.get_event_loop()

    await loop.create_server(app.make_handler(), '127.0.0.1', 5000)


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

        async def send_analytics_event(evt):
            "Send analytics event to service"
            try:
                await self.call('at.analytics.insert_event', evt)
            except ApplicationError:
                # TODO: How to get this error to Sentry?
                logger.exception("Could not reach analytics service!")
                # Serialize event to logs
                logger.info("Event: %s", evt)

        async def create_analytics_event(request, resp, t):
            "Create analytics event from request and response objects, then send it"
            try:
                rh = request.headers
                # Get cookie if present
                browser_id = request.cookies.get('browser_id')
                if browser_id and len(browser_id) != 36:
                    logger.warn("Invalid browser ID: %s", browser_id)
                    browser_id = None
                # Generate browser id if not present
                if not browser_id:
                    browser_id = str(uuid.uuid4())
                    resp.set_cookie("browser_id", browser_id, max_age=3153600000)
                evt = [
                    # event_type
                    "pageview",
                    # user_id
                    None,
                    # browser_id
                    browser_id,
                    # request_url: url path, including query string
                    str(request.rel_url),
                    # request_ip
                    rh.get("X-Real-IP"),
                    # request_method
                    request.method,
                    # request_referer
                    rh.get("Referer"),
                    # request_user_agent
                    rh.get("User-Agent"),
                    # response_status
                    int(resp.status),
                    # response_length
                    int(resp.content_length),
                    # response_time_taken FLOAT
                    t,
                    # extra JSONB
                    None
                ]
                await send_analytics_event(evt)
            except Exception:
                logger.exception("Failed to create or send analytics event")


        async def pageview_middleware(app, handler):
            async def middleware_handler(request):
                # Seconds since epoch
                t1 = time()
                resp = await handler(request)
                t2 = time()
                try:
                    # Schedule but don't wait for it
                    asyncio.ensure_future(create_analytics_event(request, resp, t2-t1))
                except Exception:
                    logger.exception("Failed to schedule create_analytics_event")
                # Always send response
                finally:
                    return resp
            return middleware_handler

        # Pass SiteComponent so WAMP can be used from within http responses
        # Pass list of middlewares
        await site_factory(self, [pageview_middleware])

    # def onLeave(self, details):
    #     print("session left")
    #
    def onDisconnect(self):
        logger.warn("transport disconnected, stopping event loop...")
        asyncio.get_event_loop().stop()


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

    l.close()
    logger.info("Loop closed")
