import asyncio

import discord
from discord.ext import commands

from utils.birthdays import start_birthday_scheduler
from utils.deploy import register_commands
from utils.heartbeat import start_heartbeat
from utils.owner import resolve_owner_ids

STATUS_INTERVAL_S = 60


async def update_status(bot: discord.Bot):
    guild_count = len(bot.guilds)
    member_count = sum(g.member_count or 0 for g in bot.guilds)
    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{guild_count} servers and {member_count} members.",
        ),
    )


async def status_loop(bot: discord.Bot):
    while True:
        await asyncio.sleep(STATUS_INTERVAL_S)
        try:
            await update_status(bot)
        except Exception:
            pass


class Ready(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.started = False

    @commands.Cog.listener()
    async def on_ready(self):
        # on_ready fires again after a reconnect; the setup below must run once
        if self.started:
            return
        self.started = True

        print("ready")

        # resolve owner id(s) from the application (team members or single owner)
        await resolve_owner_ids(self.bot)

        # keep slash commands in sync with the code on every startup
        try:
            count = await register_commands(self.bot)
            print(f"registered {count} slash commands")
        except Exception as err:
            print(f"failed to register slash commands: {err!r}")

        await update_status(self.bot)
        self.bot.loop.create_task(status_loop(self.bot))

        start_heartbeat(self.bot)
        start_birthday_scheduler(self.bot)


def setup(bot: discord.Bot):
    bot.add_cog(Ready(bot))
