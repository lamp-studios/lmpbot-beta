import discord
from aiohttp import web

# typed keys for values stored on the aiohttp app, read by handlers as request.app[KEY]
BOT = web.AppKey("bot", discord.Bot)
API_KEY = web.AppKey("api_key", bytes)
