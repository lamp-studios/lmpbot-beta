import discord
from discord.ext import commands

from utils.db import delete_guild_var, set_guild_var


class SetVerificationRole(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(
        name="set_verification_role",
        description="Set a verification role (required).",
        default_member_permissions=discord.Permissions(administrator=True),
    )
    async def set_verification_role(
        self,
        ctx: discord.ApplicationContext,
        role: discord.Option(
            discord.Role, description="Role to set as verification role.", required=False, default=None
        ),
    ):
        if not role:
            await delete_guild_var(ctx.guild.id, "verification_role")
            await delete_guild_var(ctx.guild.id, "verification_enabled")
            await ctx.respond("Removed verification role!", ephemeral=True)
        else:
            await set_guild_var(ctx.guild.id, "verification_role", role.id)
            await set_guild_var(ctx.guild.id, "verification_enabled", "true")
            await ctx.respond(f"Set {role.mention} as verified role successfully!", ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(SetVerificationRole(bot))
