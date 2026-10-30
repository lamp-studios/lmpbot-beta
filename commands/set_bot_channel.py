import discord
from discord.ext import commands

from utils.db import delete_guild_var, get_guild_var, set_guild_var

TRAP_KEY = "dont_talk_channel"
LOG_KEY = "dont_talk_logging_channel"


class SetBotChannel(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(
        name="set_bot_channel",
        description="Set a channel to detect people as bots (required).",
        default_member_permissions=discord.Permissions(ban_members=True),
    )
    async def set_bot_channel(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(
            discord.TextChannel,
            description="Channel to set as a dont talk channel.",
            required=False,
            default=None,
        ),
        log_channel: discord.Option(
            discord.TextChannel,
            description="Channel where detected spambots are logged.",
            required=False,
            default=None,
        ),
    ):
        guild_id = ctx.guild.id

        # no options at all still means "turn the whole thing off"
        if not channel and not log_channel:
            await delete_guild_var(guild_id, TRAP_KEY)
            await delete_guild_var(guild_id, LOG_KEY)
            await ctx.respond("Removed the dont_talk channel and its log channel.", ephemeral=True)
            return

        # either option can be set on its own, so neither path assumes the other ran
        changes = []
        if channel:
            await set_guild_var(guild_id, TRAP_KEY, channel.id)
            changes.append(f"dont_talk channel → {channel.mention}")
        if log_channel:
            await set_guild_var(guild_id, LOG_KEY, log_channel.id)
            changes.append(f"Log channel → {log_channel.mention}")

        # a log channel on its own is valid but does nothing until a trap exists
        trap = channel or await get_guild_var(guild_id, TRAP_KEY)
        warning = (
            ""
            if trap
            else "\n\n*No dont_talk channel is set, so nothing will be logged yet. Set one "
            "with `/set_bot_channel channel:#some-channel`.*"
        )

        await ctx.respond("Updated:\n- " + "\n- ".join(changes) + warning, ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(SetBotChannel(bot))
