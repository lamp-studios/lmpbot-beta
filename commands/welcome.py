import aiohttp
import discord
from discord.ext import commands

from utils.owner import is_owner_cached

KILL_SWITCH_URL = "https://api.uniqueweb.site/v2/botwelcome/status/disabled"


async def is_disabled() -> bool:
    """
    Remote kill-switch: Top.gg mass-mention rules can disable this command.
    Fail closed: if the site doesn't reply, treat the command as disabled.
    """
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
            async with session.get(KILL_SWITCH_URL) as res:
                return (await res.text()).strip() == "true"
    except Exception:
        # timeout / connection refused / DNS failure all land here
        return True


class Welcome(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(
        name="welcome",
        description="Command is disabled.",
        default_member_permissions=discord.Permissions(administrator=True),
    )
    async def welcome(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(
            discord.TextChannel, description="The channel to send the messages in.", required=True
        ),
        mentions: discord.Option(
            bool, description="Mentions every members in the messages if true", required=True
        ),
        welcome_message: discord.Option(
            str, description="The welcome message", required=False, default=None
        ),
    ):
        # owner-only
        if not is_owner_cached(self.bot, ctx.author.id):
            await ctx.respond("This command is owner-only.", ephemeral=True)
            return

        if await is_disabled():
            await ctx.respond("Due to Top.gg's rules, the /welcome is removed for the time being.", ephemeral=True)
            return

        await ctx.respond("Sending welcome messages...", ephemeral=True)

        allowed_mentions = (
            discord.AllowedMentions(everyone=False, roles=False, users=True, replied_user=False)
            if mentions
            else discord.AllowedMentions.none()
        )

        guild = ctx.guild
        members = guild.members if guild.chunked else await guild.chunk()
        for member in members:
            await channel.send(
                f"\nWelcome {member.mention} to **{guild.name}**!\n\nMake sure to read the rules/messages!",
                allowed_mentions=allowed_mentions,
            )


def setup(bot: discord.Bot):
    bot.add_cog(Welcome(bot))
