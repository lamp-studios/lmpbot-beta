import discord


def setup(bot: discord.Bot):
    @bot.slash_command(
        name="welcome",
        description="Resends all welcome messages of all members to a specified channel.",
        default_member_permissions=discord.Permissions(administrator=True),
    )
    async def welcome_cmd(
        ctx: discord.ApplicationContext,
        channel: discord.TextChannel = discord.Option(
            discord.TextChannel, "The channel to send the messages in."
        ),
        mentions: bool = discord.Option(
            bool, "Mentions every members in the messages if true"
        ),
        welcome_message: str = discord.Option(
            str, "The welcome message", required=False, default=None
        ),
    ):
        await ctx.respond("Sending welcome messages...", ephemeral=True)

        mention_setting = discord.AllowedMentions.all() if mentions else discord.AllowedMentions.none()

        for member in ctx.guild.members:
            await channel.send(
                f"\nWelcome {member.mention} to **{ctx.guild.name}**!\n\nMake sure to read the messages!",
                allowed_mentions=mention_setting,
            )
