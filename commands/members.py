import discord
from discord import app_commands
from utils import db


@app_commands.command(name="members", description="See all verified members.")
async def members_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    verified = []
    for member in interaction.guild.members:
        if await db.get_member_var(interaction.guild_id, member.id, "is_verified") == "true":
            verified.append(member.mention)

    text = "\n".join(verified) if verified else "None"
    await interaction.followup.send(text, allowed_mentions=discord.AllowedMentions.none())


def setup(tree: app_commands.CommandTree):
    tree.add_command(members_cmd)
