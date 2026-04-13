import discord


def setup(bot: discord.Bot):
    @bot.event
    async def on_interaction(interaction: discord.Interaction):
        # handle button interactions not covered by application commands
        if interaction.type != discord.InteractionType.component:
            return

        if interaction.data.get("custom_id") == "learnmore":
            await interaction.response.send_message(
                "To automatically ban/kick bots, since most popular discord bots don't "
                "have that feature, *yet*. We had to make our own for our server.",
                ephemeral=True,
            )
