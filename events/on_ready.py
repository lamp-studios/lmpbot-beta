import discord
from discord.ext import tasks


def setup(bot: discord.Bot):
    @tasks.loop(minutes=1)
    async def update_status():
        guild_count = len(bot.guilds)
        member_count = sum(g.member_count or 0 for g in bot.guilds)
        await bot.change_presence(
            status=discord.Status.dnd,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{guild_count} servers and {member_count} members.",
            ),
        )

    @bot.event
    async def on_ready():
        print("ready")
        update_status.start()
