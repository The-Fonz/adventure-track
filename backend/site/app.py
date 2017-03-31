import asyncio
from aiohttp import web


async def handle(request):
    name = request.match_info.get('name', 'Anonymous')
    return web.Response(text="Hello "+name)


if __name__=="__main__":
    app = web.Application()
    app.router.add_get('/', handle)
    app.router.add_get('/{name}', handle)

    loop = asyncio.get_event_loop()

    coro = loop.create_server(app.make_handler(), '127.0.0.1', 5000)
    loop.run_until_complete(coro)
    print("Server created")
    loop.run_forever()
    # web.run_app(app, port=5000)
