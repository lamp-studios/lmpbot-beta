import discord


def setup(client: discord.Client):
    @client.event
    async def on_guild_join(guild: discord.Guild):
        print(f"{guild.name} now has the bot!")
