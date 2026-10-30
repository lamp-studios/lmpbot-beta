import discord
from discord.ext import commands

from utils.db import delete_guild_var, set_guild_var


class SetForumChannel(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(
        name="set_forum_channel",
        description="Sets the forum channel where staff are automatically added to new posts.",
        default_member_permissions=discord.Permissions(administrator=True),
    )
    async def set_forum_channel(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(
            discord.ForumChannel,
            description="Channel to set as a forum channel.",
            required=False,
            default=None,
        ),
        role: discord.Option(discord.Role, description="Role to set (optional).", required=False, default=None),
    ):
        parts = []

        if not channel:
            await delete_guild_var(ctx.guild.id, "forum_channel")
            parts.append("Removed forum channel from adding admins in new posts!")
        else:
            await set_guild_var(ctx.guild.id, "forum_channel", channel.id)
            parts.append(f"Set {channel.mention} as forum channel successfully!")

        if role:
            await set_guild_var(ctx.guild.id, "staff_role", role.id)
            parts.append(f"Staff role set to {role.mention}!")

        await ctx.respond("\n".join(parts), ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(SetForumChannel(bot))
