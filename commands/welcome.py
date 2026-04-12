import discord
from discord import app_commands


@app_commands.command(
    name="welcome",
    description="Resends all welcome messages of all members to a specified channel.",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    channel="The channel to send the messages in.",
    mentions="Mentions every members in the messages if true",
    welcome_message="The welcome message",
)
async def welcome_cmd(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    mentions: bool,
    welcome_message: str | None = None,
):
    await interaction.response.send_message("Sending welcome messages...", ephemeral=True)

    mention_setting = discord.AllowedMentions.all() if mentions else discord.AllowedMentions.none()

    for member in interaction.guild.members:
        await channel.send(
            f"\nWelcome {member.mention} to **{interaction.guild.name}**!\n\nMake sure to read the rules!",
            allowed_mentions=mention_setting,
        )


def setup(tree: app_commands.CommandTree):
    tree.add_command(welcome_cmd)
