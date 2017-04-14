import re
import json
import signal
import asyncio

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

        async def public_insert_event(browser_evt, details):
            "Event logging for browser. Returns True if succeeded"
            evt = []
            try:
                session = await self.call('wamp.session.get', details.caller)
                h = session['transport']['http_headers_received']
                # Convert all keys to lowercase, just in case (pun intended)
                h = dict((k.lower(), v) for k,v in h.items())
                evt += [browser_evt['type']]
                # user_id is None
                evt += [None]
                # browser_id
                browser_id = None
                # First get cookie or empty string and eliminate whitespace
                try: browser_id = re.search('browser_id=([\d\w-]*);?', h.get('cookie','').replace(' ', '')).group(1)
                # No group
                except (IndexError, AttributeError): pass
                evt += [browser_id]
                # request_url, request_ip, request_method
                evt += [None, h['x-real-ip'], 'websocket']
                # request_referer, request_user_agent
                evt += [h.get('referer'), h['user-agent']]
                # response_status, response_length, response_time_taken
                evt += [None, None, None]
                # extra: JSON object with more info
                extra = browser_evt.get('extra', None)
                if extra: extra = json.dumps(extra)
                # Avoid filling up db, limit to 100kB
                if len(extra) > 1E5: raise Exception("evt['extra'] json is too large")
                evt += [extra]
                await self.db.insert_event(evt)
                return True
            except Exception:
                logger.exception("Something went wrong when trying to construct or log analytics event")
                return False

        self.register(public_insert_event, 'at.public.analytics.insert_event',
                      RegisterOptions(details_arg='details'))

        await site_factory(self)


if __name__=="__main__":
    AnalyticsComponent.run_forever()
