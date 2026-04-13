import discord


def setup(bot: discord.Bot):
    @bot.event
    async def on_guild_join(guild: discord.Guild):
        print(f"{guild.name} now has the bot!")
