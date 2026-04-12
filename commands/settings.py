import discord
from discord import app_commands
from utils import db

# all admin-only guild config commands grouped together


@app_commands.command(
    name="set_chatbot_channel",
    description="Set a channel to have an AI in.",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="Channel to set as a chatbot channel.")
async def set_chatbot_channel(
    interaction: discord.Interaction,
    channel: discord.TextChannel | None = None,
):
    if channel is None:
        await db.delete_guild_var(interaction.guild_id, "chatbot_channel")
        await interaction.response.send_message("Removed chatbot channel!", ephemeral=True)
    else:
        await db.set_guild_var(interaction.guild_id, "chatbot_channel", str(channel.id))
        await interaction.response.send_message(
            f"Set {channel.mention} as chatbot channel successfully!", ephemeral=True
        )


@app_commands.command(
    name="set_bot_channel",
    description="Set a channel to detect people as bots (required).",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="Channel to set as a dont talk channel.")
async def set_bot_channel(
    interaction: discord.Interaction,
    channel: discord.TextChannel | None = None,
):
    if channel is None:
        await db.delete_guild_var(interaction.guild_id, "dont_talk_channel")
        await interaction.response.send_message("Removed dont_talk channel!", ephemeral=True)
    else:
        await db.set_guild_var(interaction.guild_id, "dont_talk_channel", str(channel.id))
        await interaction.response.send_message(
            f"Set {channel.mention} as dont_talk channel successfully!", ephemeral=True
        )


@app_commands.command(
    name="set_forum_channel",
    description="Sets the forum channel where staff are automatically added to new posts.",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    channel="Channel to set as a forum channel.",
    role="Role to set (optional).",
)
async def set_forum_channel(
    interaction: discord.Interaction,
    channel: discord.ForumChannel | None = None,
    role: discord.Role | None = None,
):
    parts = []

    if channel is None:
        await db.delete_guild_var(interaction.guild_id, "forum_channel")
        parts.append("Removed forum channel from adding admins in new posts!")
    else:
        await db.set_guild_var(interaction.guild_id, "forum_channel", str(channel.id))
        parts.append(f"Set {channel.mention} as forum channel successfully!")

    if role is not None:
        await db.set_guild_var(interaction.guild_id, "staff_role", str(role.id))
        parts.append(f"Staff role set to {role.mention}!")

    await interaction.response.send_message("\n".join(parts), ephemeral=True)


@app_commands.command(
    name="set_news_channel",
    description="Sets the news channel where bot news are sent in.",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="Channel to set as a bot news channel.")
async def set_news_channel(
    interaction: discord.Interaction,
    channel: discord.TextChannel | None = None,
):
    if channel is None:
        await db.delete_guild_var(interaction.guild_id, "news_channel")
        await interaction.response.send_message(
            "Removed channel from having bot news sent in.", ephemeral=True
        )
    else:
        await db.set_guild_var(interaction.guild_id, "news_channel", str(channel.id))
        await interaction.response.send_message(
            f"Set {channel.mention} as news channel successfully!", ephemeral=True
        )


@app_commands.command(
    name="set_verification_role",
    description="Set a verification role (required).",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(role="Role to set as verification role.")
async def set_verification_role(
    interaction: discord.Interaction,
    role: discord.Role | None = None,
):
    if role is None:
        await db.delete_guild_var(interaction.guild_id, "verification_role")
        await interaction.response.send_message("Removed verification role!", ephemeral=True)
    else:
        await db.set_guild_var(interaction.guild_id, "verification_role", str(role.id))
        await interaction.response.send_message(
            f"Set {role.mention} as verified role successfully!", ephemeral=True
        )


def setup(tree: app_commands.CommandTree):
    for cmd in (
        set_chatbot_channel,
        set_bot_channel,
        set_forum_channel,
        set_news_channel,
        set_verification_role,
    ):
        tree.add_command(cmd)
