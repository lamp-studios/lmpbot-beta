import discord
from discord.ext import tasks


def setup(client: discord.Client):
    @tasks.loop(minutes=1)
    async def update_status():
        guild_count = len(client.guilds)
        member_count = sum(g.member_count or 0 for g in client.guilds)
        await client.change_presence(
            status=discord.Status.dnd,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{guild_count} servers and {member_count} members.",
            ),
        )

    @client.event
    async def on_ready():
        print("ready")
        await client.tree.sync()
        update_status.start()
