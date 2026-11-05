"""
Route registry. Each module here exposes `routes`, a `web.RouteTableDef`.

To add an endpoint, write a handler in a module in this package (or a new one),
then list that module's `routes` in ROUTE_TABLES. Every handler requires the API
key unless it is decorated with `api.middleware.public`.
"""

from aiohttp import web

from api.routes import guilds, health

ROUTE_TABLES = [health.routes, guilds.routes]


def setup_routes(app: web.Application) -> None:
    for table in ROUTE_TABLES:
        app.add_routes(table)
