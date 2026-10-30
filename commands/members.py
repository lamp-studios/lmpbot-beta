import discord
from discord.ext import commands

from utils.db import get_member_var


class Members(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(name="members", description="See all verified members.")
    async def members(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)

        guild = ctx.guild
        members = guild.members if guild.chunked else await guild.chunk()

        verified = []
        for member in members:
            if await get_member_var(guild.id, member.id, "is_verified") == "true":
                verified.append(member.mention)

        text = "\n".join(verified) if verified else "None"
        await ctx.respond(text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())


def setup(bot: discord.Bot):
    bot.add_cog(Members(bot))
