import discord
from discord.ext import commands

from utils.db import delete_guild_var, set_guild_var


class SetChatbotChannel(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(
        name="set_chatbot_channel",
        description="Set a channel to have an AI in.",
        default_member_permissions=discord.Permissions(administrator=True),
    )
    async def set_chatbot_channel(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(
            discord.TextChannel,
            description="Channel to set as a chatbot channel.",
            required=False,
            default=None,
        ),
    ):
        if not channel:
            await delete_guild_var(ctx.guild.id, "chatbot_channel")
            await ctx.respond("Removed chatbot channel!", ephemeral=True)
        else:
            await set_guild_var(ctx.guild.id, "chatbot_channel", channel.id)
            await ctx.respond(f"Set {channel.mention} as chatbot channel successfully!", ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(SetChatbotChannel(bot))
