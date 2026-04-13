import discord
from utils import db


def setup(bot: discord.Bot):
    @bot.slash_command(name="members", description="See all verified members.")
    async def members_cmd(ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)

        verified = []
        for member in ctx.guild.members:
            if await db.get_member_var(ctx.guild.id, member.id, "is_verified") == "true":
                verified.append(member.mention)

        text = "\n".join(verified) if verified else "None"
        await ctx.followup.send(text, allowed_mentions=discord.AllowedMentions.none())
