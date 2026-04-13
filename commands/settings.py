import discord
from utils import db

# all admin-only guild config commands grouped together


def setup(bot: discord.Bot):
    admin = discord.Permissions(administrator=True)

    @bot.slash_command(
        name="set_chatbot_channel",
        description="Set a channel to have an AI in.",
        default_member_permissions=admin,
    )
    async def set_chatbot_channel(
        ctx: discord.ApplicationContext,
        channel: discord.TextChannel = discord.Option(
            discord.TextChannel, "Channel to set as a chatbot channel.", required=False, default=None
        ),
    ):
        if channel is None:
            await db.delete_guild_var(ctx.guild.id, "chatbot_channel")
            await ctx.respond("Removed chatbot channel!", ephemeral=True)
        else:
            await db.set_guild_var(ctx.guild.id, "chatbot_channel", str(channel.id))
            await ctx.respond(
                f"Set {channel.mention} as chatbot channel successfully!", ephemeral=True
            )

    @bot.slash_command(
        name="set_bot_channel",
        description="Set a channel to detect people as bots (required).",
        default_member_permissions=admin,
    )
    async def set_bot_channel(
        ctx: discord.ApplicationContext,
        channel: discord.TextChannel = discord.Option(
            discord.TextChannel, "Channel to set as a dont talk channel.", required=False, default=None
        ),
    ):
        if channel is None:
            await db.delete_guild_var(ctx.guild.id, "dont_talk_channel")
            await ctx.respond("Removed dont_talk channel!", ephemeral=True)
        else:
            await db.set_guild_var(ctx.guild.id, "dont_talk_channel", str(channel.id))
            await ctx.respond(
                f"Set {channel.mention} as dont_talk channel successfully!", ephemeral=True
            )

    @bot.slash_command(
        name="set_forum_channel",
        description="Sets the forum channel where staff are automatically added to new posts.",
        default_member_permissions=admin,
    )
    async def set_forum_channel(
        ctx: discord.ApplicationContext,
        channel: discord.ForumChannel = discord.Option(
            discord.ForumChannel, "Channel to set as a forum channel.", required=False, default=None
        ),
        role: discord.Role = discord.Option(discord.Role, "Role to set (optional).", required=False, default=None),
    ):
        parts = []

        if channel is None:
            await db.delete_guild_var(ctx.guild.id, "forum_channel")
            parts.append("Removed forum channel from adding admins in new posts!")
        else:
            await db.set_guild_var(ctx.guild.id, "forum_channel", str(channel.id))
            parts.append(f"Set {channel.mention} as forum channel successfully!")

        if role is not None:
            await db.set_guild_var(ctx.guild.id, "staff_role", str(role.id))
            parts.append(f"Staff role set to {role.mention}!")

        await ctx.respond("\n".join(parts), ephemeral=True)

    @bot.slash_command(
        name="set_news_channel",
        description="Sets the news channel where bot news are sent in.",
        default_member_permissions=admin,
    )
    async def set_news_channel(
        ctx: discord.ApplicationContext,
        channel: discord.TextChannel = discord.Option(
            discord.TextChannel, "Channel to set as a bot news channel.", required=False, default=None
        ),
    ):
        if channel is None:
            await db.delete_guild_var(ctx.guild.id, "news_channel")
            await ctx.respond(
                "Removed channel from having bot news sent in.", ephemeral=True
            )
        else:
            await db.set_guild_var(ctx.guild.id, "news_channel", str(channel.id))
            await ctx.respond(
                f"Set {channel.mention} as news channel successfully!", ephemeral=True
            )

    @bot.slash_command(
        name="set_verification_role",
        description="Set a verification role (required).",
        default_member_permissions=admin,
    )
    async def set_verification_role(
        ctx: discord.ApplicationContext,
        role: discord.Role = discord.Option(
            discord.Role, "Role to set as verification role.", required=False, default=None
        ),
    ):
        if role is None:
            await db.delete_guild_var(ctx.guild.id, "verification_role")
            await ctx.respond("Removed verification role!", ephemeral=True)
        else:
            await db.set_guild_var(ctx.guild.id, "verification_role", str(role.id))
            await ctx.respond(
                f"Set {role.mention} as verified role successfully!", ephemeral=True
            )
