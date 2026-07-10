import {
  SlashCommandBuilder,
  PermissionFlagsBits,
  ChannelType,
  MessageFlags,
} from "discord.js";
import { setGuildVar, deleteGuildVar } from "../utils/db.js";

export default {
  data: new SlashCommandBuilder()
    .setName("set_chatbot_channel")
    .setDescription("Set a channel to have an AI in.")
    .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
    .addChannelOption((o) =>
      o
        .setName("channel")
        .setDescription("Channel to set as a chatbot channel.")
        .addChannelTypes(ChannelType.GuildText)
        .setRequired(false)
    ),

  async execute(interaction) {
    const channel = interaction.options.getChannel("channel");
    if (!channel) {
      await deleteGuildVar(interaction.guild.id, "chatbot_channel");
      await interaction.reply({ content: "Removed chatbot channel!", flags: MessageFlags.Ephemeral });
    } else {
      await setGuildVar(interaction.guild.id, "chatbot_channel", channel.id);
      await interaction.reply({
        content: `Set ${channel} as chatbot channel successfully!`,
        flags: MessageFlags.Ephemeral,
      });
    }
  },
};
