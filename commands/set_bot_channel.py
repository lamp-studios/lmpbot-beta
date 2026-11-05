import discord
from discord.ext import commands

from utils.db import delete_guild_var, get_guild_var, set_guild_var

TRAP_KEY = "dont_talk_channel"
LOG_KEY = "dont_talk_logging_channel"
WARNING_KEY = "dont_talk_warning_message"


class ChatWarningView(discord.ui.DesignerView):
    def __init__(self):
        super().__init__(timeout=None)

        learn_more = discord.ui.Button(
            label="Learn more",
            style=discord.ButtonStyle.primary,
            custom_id="learnmore",
        )

        container = discord.ui.Container(
            discord.ui.TextDisplay("# Do **NOT** talk in this channel normally."),
            discord.ui.TextDisplay(
                "## Talking in this channel risks you getting **soft-banned**!"
            ),
            discord.ui.Separator(divider=True, spacing=discord.SeparatorSpacingSize.small),
            discord.ui.Section(
                discord.ui.TextDisplay("*This is to help the server from spambots.*"),
                accessory=learn_more,
            ),
            colour=discord.Colour(0xFF2B00),
        )
        self.add_item(container)


class SetBotChannel(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    async def _delete_warning(self, guild: discord.Guild) -> bool:
        """Deletes the stored warning message. Returns False if missing perms."""
        channel_id = await get_guild_var(guild.id, TRAP_KEY)
        message_id = await get_guild_var(guild.id, WARNING_KEY)
        ok = True

        if channel_id and message_id:
            channel = guild.get_channel(int(channel_id))
            if channel:
                try:
                    await channel.get_partial_message(int(message_id)).delete()
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    ok = False

        await delete_guild_var(guild.id, WARNING_KEY)
        return ok

    @discord.slash_command(
        name="set_bot_channel",
        description="Set a channel to detect people as bots (required).",
        default_member_permissions=discord.Permissions(ban_members=True),
    )
    @discord.option(
        "channel",
        discord.TextChannel,
        description="Channel to set as a dont talk channel.",
        required=False,
        default=None,
    )
    @discord.option(
        "log_channel",
        discord.TextChannel,
        description="Channel where detected spambots are logged.",
        required=False,
        default=None,
    )
    async def set_bot_channel(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.TextChannel | None,
        log_channel: discord.TextChannel | None,
    ):
        guild = ctx.guild
        guild_id = guild.id
        extra = ""

        # no options at all still means "turn the whole thing off"
        if not channel and not log_channel:
            if not await self._delete_warning(guild):
                extra = "\n\n*Couldn't delete the warning message, I'm missing perms there.*"
            await delete_guild_var(guild_id, TRAP_KEY)
            await delete_guild_var(guild_id, LOG_KEY)
            await ctx.respond(
                "Removed the dont_talk channel and its log channel." + extra,
                ephemeral=True,
            )
            return

        changes = []

        if channel:
            # remove the old warning BEFORE overwriting the trap channel id
            if not await self._delete_warning(guild):
                extra = "\n\n*Couldn't delete the old warning message, I'm missing perms there.*"

            await set_guild_var(guild_id, TRAP_KEY, channel.id)

            try:
                msg = await channel.send(view=ChatWarningView())
                await set_guild_var(guild_id, WARNING_KEY, msg.id)
            except discord.Forbidden:
                extra += f"\n\n*I can't send messages in {channel.mention}, so no warning was posted.*"

            changes.append(f"dont_talk channel → {channel.mention}")

        if log_channel:
            await set_guild_var(guild_id, LOG_KEY, log_channel.id)
            changes.append(f"Log channel → {log_channel.mention}")

        # a log channel on its own is valid but does nothing until a trap exists
        trap = channel or await get_guild_var(guild_id, TRAP_KEY)
        if not trap:
            extra += (
                "\n\n*No dont_talk channel is set, so nothing will be logged yet. Set one "
                "with `/set_bot_channel channel:#some-channel`.*"
            )

        await ctx.respond("Updated:\n- " + "\n- ".join(changes) + extra, ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(SetBotChannel(bot))