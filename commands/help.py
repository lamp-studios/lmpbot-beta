import discord


def setup(bot: discord.Bot):
    @bot.slash_command(
        name="help",
        description="See all commands and what they do (includes prefix commands).",
    )
    async def help_cmd(
        ctx: discord.ApplicationContext,
        command: str = discord.Option(
            str, "Command to show help for.", required=False, default=None
        ),
    ):
        text = (
            "# Help - CMDS\n"
            "## **Slash Commands:**\n"
            "- /help (Shows this message)\n"
            "- /set_verification_role (REQUIRED FOR VERIFICATION, OWNER ONLY, "
            "set a role for the user to get when the user finishes verifying)\n"
            "- /members (ADMINS ONLY, shows every verified members, "
            "only the specified member will be shown if the option is specified)\n"
            "- /welcome (ADMINS ONLY, read autocomplete)\n"
            "## **Prefix Commands: (.)**\n"
            "- .up (OWNER ONLY, updates all cmds)\n"
            "- .exe (OWNER ONLY, evals a specified command)\n"
        )
        await ctx.respond(text, ephemeral=True)
