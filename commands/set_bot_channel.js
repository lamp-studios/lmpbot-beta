import {
  SlashCommandBuilder,
  PermissionFlagsBits,
  ChannelType,
  MessageFlags,
} from "discord.js";
import { setGuildVar, deleteGuildVar } from "../utils/db.js";

export default {
  data: new SlashCommandBuilder()
    .setName("set_bot_channel")
    .setDescription("Set a channel to detect people as bots (required).")
    .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
    .addChannelOption((o) =>
      o
        .setName("channel")
        .setDescription("Channel to set as a dont talk channel.")
        .addChannelTypes(ChannelType.GuildText)
        .setRequired(false)
    ),

  async execute(interaction) {
    const channel = interaction.options.getChannel("channel");
    if (!channel) {
      await deleteGuildVar(interaction.guild.id, "dont_talk_channel");
      await interaction.reply({ content: "Removed dont_talk channel!", flags: MessageFlags.Ephemeral });
    } else {
      await setGuildVar(interaction.guild.id, "dont_talk_channel", channel.id);
      await interaction.reply({
        content: `Set ${channel} as dont_talk channel successfully!`,
        flags: MessageFlags.Ephemeral,
      });
    }
  },
};
