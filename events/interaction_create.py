import traceback

import discord
from discord.ext import commands


class InteractionCreate(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx: discord.ApplicationContext, error: Exception):
        original = getattr(error, "original", error)
        print(f"Error running /{ctx.command.qualified_name if ctx.command else '?'}:")
        traceback.print_exception(type(original), original, original.__traceback__)

        try:
            # respond() follows up instead once the interaction was answered or deferred
            await ctx.respond("Something went wrong running that command.", ephemeral=True)
        except Exception:
            pass

    # A plain listener runs alongside py-cord's own on_interaction, so slash
    # commands, autocomplete and views keep being dispatched as normal.
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type is not discord.InteractionType.component:
            return
        if (interaction.data or {}).get("custom_id") != "learnmore":
            return

        await interaction.response.send_message(
            "To automatically ban/kick bots, since most popular discord bots don't "
            "have that feature, *yet*. We had to make our own for our server.",
            ephemeral=True,
        )


def setup(bot: discord.Bot):
    bot.add_cog(InteractionCreate(bot))
