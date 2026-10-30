import discord
from discord.ext import commands


class GuildCreate(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        print(f"{guild.name} now has the bot!")


def setup(bot: discord.Bot):
    bot.add_cog(GuildCreate(bot))
