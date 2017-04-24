import asyncio
import aioconsole

from backend.utils import BackendAppSession, getLogger

logger = getLogger('interactive_wamp_session')

l = asyncio.get_event_loop()

class InteractiveComponent(BackendAppSession):

    async def onJoin(self, details):
        logger.info("session joined")

        server = await aioconsole.start_interactive_server(
            host='localhost',
            port=8000
        )
        l.wampsess = self

        while True:
            await asyncio.sleep(10)


if __name__=="__main__":
    print("""
    Connect with netstat by running > nc localhost 8000
    Access the WAMP session as loop.wampsess
    E.g. >>> await loop.wampsess.call('some.func.route', arg1, arg2, kwarg='hi')
    """)
    InteractiveComponent.run_forever()
