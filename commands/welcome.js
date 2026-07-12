import {
  SlashCommandBuilder,
  PermissionFlagsBits,
  ChannelType,
  MessageFlags,
} from "discord.js";

export default {
  data: new SlashCommandBuilder()
    .setName("welcome")
    .setDescription("Command is disabled.")
    .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
    .addChannelOption((o) =>
      o
        .setName("channel")
        .setDescription("The channel to send the messages in.")
        .addChannelTypes(ChannelType.GuildText)
        .setRequired(true)
    )
    .addBooleanOption((o) =>
      o
        .setName("mentions")
        .setDescription("Mentions every members in the messages if true")
        .setRequired(true)
    )
    .addStringOption((o) =>
      o.setName("welcome_message").setDescription("The welcome message").setRequired(false)
    ),

  async execute(interaction) {
    // owner-only (mirrors @commands.is_owner())
    if (!interaction.client.ownerIds.has(interaction.user.id)) {
      await interaction.reply({
        content: "This command is owner-only.",
        flags: MessageFlags.Ephemeral,
      });
      return;
    }

    const channel = interaction.options.getChannel("channel");
    const mentions = interaction.options.getBoolean("mentions");

    // remote kill-switch: Top.gg mass-mention rules can disable this command.
    // Fail closed — if the site doesn't reply, treat the command as disabled.
    let disabled = true;
    try {
      const res = await fetch("https://api.uniqueweb.site/v2/botwelcome/status/disabled", {
        signal: AbortSignal.timeout(2000),
      });
      disabled = (await res.text()).trim() === "true";
    } catch {
      // timeout / connection refused / DNS failure all land here
      disabled = true;
    }

    if (disabled) {
      await interaction.reply({
        content: "Due to Top.gg's rules, the /welcome is removed for the time being.",
        flags: MessageFlags.Ephemeral,
      });
      return;
    }

    await interaction.reply({
      content: "Sending welcome messages...",
      flags: MessageFlags.Ephemeral,
    });

    const allowedMentions = mentions ? { parse: ["users"] } : { parse: [] };

    const members = await interaction.guild.members.fetch();
    for (const member of members.values()) {
      await channel.send({
        content: `\nWelcome ${member} to **${interaction.guild.name}**!\n\nMake sure to read the rules/messages!`,
        allowedMentions,
      });
    }
  },
};
