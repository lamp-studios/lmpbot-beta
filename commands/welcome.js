import {
  SlashCommandBuilder,
  PermissionFlagsBits,
  ChannelType,
  MessageFlags,
} from "discord.js";

export default {
  data: new SlashCommandBuilder()
    .setName("welcome")
    .setDescription("Resends all welcome messages of all members to a specified channel.")
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
    const channel = interaction.options.getChannel("channel");
    const mentions = interaction.options.getBoolean("mentions");
    const isallowed = await fetch("https://")

    await interaction.reply({
      content: "Sending welcome messages...",
      flags: MessageFlags.Ephemeral,
    });

    const allowedMentions = mentions ? { parse: ["users"] } : { parse: [] };

    const members = await interaction.guild.members.fetch();

    for (const member of members.values()) {
      await channel.send({
        content: `\nWelcome ${member} to **${interaction.guild.name}**!\n\nMake sure to read the messages!`,
        allowedMentions,
      });
    }
  },
};
