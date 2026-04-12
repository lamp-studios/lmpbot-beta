import discord
from discord import app_commands


@app_commands.command(name="help", description="See all commands and what they do (includes prefix commands).")
@app_commands.describe(command="Command to show help for.")
async def help_cmd(interaction: discord.Interaction, command: str | None = None):
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
    await interaction.response.send_message(text, ephemeral=True)


def setup(tree: app_commands.CommandTree):
    tree.add_command(help_cmd)
