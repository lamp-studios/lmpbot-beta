import json
import re

from aiohttp import web

from api.responses import json_error
from api.keys import BOT

routes = web.RouteTableDef()

MAX_GUILD_IDS = 500
SNOWFLAKE_RE = re.compile(r"^\d{17,20}$")


async def read_json(request: web.Request):
    """The parsed request body, or None if it is missing or not valid JSON."""
    raw = await request.read()  # raises 413 past the app's client_max_size
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return None


@routes.post("/guilds/check")
async def check_guilds(request: web.Request) -> web.Response:
    """Return the subset of the given guild ids that the bot is currently in."""
    body = await read_json(request)
    if not isinstance(body, dict):
        return json_error(400, "Body must be a JSON object")

    guild_ids = body.get("guildIds")
    if not isinstance(guild_ids, list):
        return json_error(400, "guildIds must be an array of strings")
    if len(guild_ids) > MAX_GUILD_IDS:
        return json_error(400, f"guildIds may contain at most {MAX_GUILD_IDS} ids")
    for gid in guild_ids:
        if not isinstance(gid, str) or not SNOWFLAKE_RE.fullmatch(gid):
            return json_error(400, "Every guildId must be a 17-20 digit snowflake string")

    bot = request.app[BOT]
    if not bot.is_ready():
        return json_error(503, "Bot not ready")

    # in-memory guild cache only; dict.fromkeys de-duplicates while keeping order
    present = [gid for gid in dict.fromkeys(guild_ids) if bot.get_guild(int(gid)) is not None]
    return web.json_response({"guildIds": present})
