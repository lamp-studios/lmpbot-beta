import discord
from discord.ext import commands

from utils.db import delete_guild_var, set_guild_var


class SetNewsChannel(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(
        name="set_news_channel",
        description="Sets the news channel where bot news are sent in.",
        default_member_permissions=discord.Permissions(administrator=True),
    )
    async def set_news_channel(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(
            discord.TextChannel,
            description="Channel to set as a bot news channel.",
            required=False,
            default=None,
        ),
    ):
        if not channel:
            await delete_guild_var(ctx.guild.id, "news_channel")
            await ctx.respond("Removed channel from having bot news sent in.", ephemeral=True)
        else:
            await set_guild_var(ctx.guild.id, "news_channel", channel.id)
            await ctx.respond(f"Set {channel.mention} as news channel successfully!", ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(SetNewsChannel(bot))
