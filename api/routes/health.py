from aiohttp import web

from api.middleware import public
from api.keys import BOT

routes = web.RouteTableDef()


@routes.get("/health")
@public
async def health(request: web.Request) -> web.Response:
    bot = request.app[BOT]
    return web.json_response({"ok": True, "ready": bot.is_ready()})
