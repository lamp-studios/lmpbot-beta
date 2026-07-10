import {
  SlashCommandBuilder,
  PermissionFlagsBits,
  ChannelType,
  MessageFlags,
} from "discord.js";
import { setGuildVar, deleteGuildVar } from "../utils/db.js";

export default {
  data: new SlashCommandBuilder()
    .setName("set_news_channel")
    .setDescription("Sets the news channel where bot news are sent in.")
    .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
    .addChannelOption((o) =>
      o
        .setName("channel")
        .setDescription("Channel to set as a bot news channel.")
        .addChannelTypes(ChannelType.GuildText)
        .setRequired(false)
    ),

  async execute(interaction) {
    const channel = interaction.options.getChannel("channel");
    if (!channel) {
      await deleteGuildVar(interaction.guild.id, "news_channel");
      await interaction.reply({
        content: "Removed channel from having bot news sent in.",
        flags: MessageFlags.Ephemeral,
      });
    } else {
      await setGuildVar(interaction.guild.id, "news_channel", channel.id);
      await interaction.reply({
        content: `Set ${channel} as news channel successfully!`,
        flags: MessageFlags.Ephemeral,
      });
    }
  },
};
