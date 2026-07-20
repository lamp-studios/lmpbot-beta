import { SlashCommandBuilder, MessageFlags } from "discord.js";

export default {
  data: new SlashCommandBuilder()
    .setName("help")
    .setDescription("See all commands and what they do (includes prefix commands).")
    .addStringOption((o) =>
      o.setName("command").setDescription("Command to show help for.").setRequired(false)
    ),

  async execute(interaction) {
    const text =
      "# Help - CMDS\n" +
      "## **Slash Commands:**\n" +
      "- /help (Shows this message)\n" +
      "- /set_verification_role (REQUIRED FOR VERIFICATION, OWNER ONLY, " +
      "set a role for the user to get when the user finishes verifying)\n" +
      "- /members (ADMINS ONLY, shows every verified members, " +
      "only the specified member will be shown if the option is specified)\n" +
      "- /welcome (ADMINS ONLY, read autocomplete)\n" +
      "- /birthday set (set your birthday, e.g. /birthday set 30/01)\n" +
      "- /birthday settings|enable|disable (ADMINS ONLY, configure birthday " +
      "role, announcement channel, custom message and ping)\n" +
      "## **Prefix Commands: (.)**\n" +
      "- .up (OWNER ONLY, updates all cmds)\n" +
      "- .exe (OWNER ONLY, evals a specified command)\n";

    await interaction.reply({ content: text, flags: MessageFlags.Ephemeral });
  },
};
