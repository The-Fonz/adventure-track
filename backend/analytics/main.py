import signal
import asyncio

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from autobahn.wamp.types import RegisterOptions
from aiohttp import web
import aiohttp_jinja2
import jinja2

from .db import Db
from ..utils import BackendAppSession, getLogger

logger = getLogger('analytics.main')


async def site_factory(wampsess):
    """
    Creates aiohttp server listening on specified port
    :param wampsession:
    :return:
    """
    @aiohttp_jinja2.template('dashboard.html')
    async def dashboard(request):
        # Pygal is nice and simple plotting library with
        # output to both interactive HTML and SVG or PNG
        # Plotly and holoview are also nice but more involved
        vis = await wampsess.db.get_daily_visitors()
        logger.info(vis)
        import pygal
        bar_chart = pygal.Bar(legend_at_bottom=True,
                        legend_at_bottom_columns=2)
        bar_chart.x_labels = vis[0]
        bar_chart.add('Total pageviews', vis[1])
        bar_chart.add('Unique visitors', vis[2])
        bar_chart = bar_chart.render().decode('utf-8')



        return {'daily_user_chart': bar_chart}

    app = web.Application()

    aiohttp_jinja2.setup(app, loader=jinja2.PackageLoader('backend.analytics'))

    app.router.add_get('/', dashboard)

    loop = asyncio.get_event_loop()

    await loop.create_server(app.make_handler(), '127.0.0.1', 5001)


class AnalyticsComponent(BackendAppSession):

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
