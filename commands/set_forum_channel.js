import {
  SlashCommandBuilder,
  PermissionFlagsBits,
  ChannelType,
  MessageFlags,
} from "discord.js";
import { setGuildVar, deleteGuildVar } from "../utils/db.js";

export default {
  data: new SlashCommandBuilder()
    .setName("set_forum_channel")
    .setDescription("Sets the forum channel where staff are automatically added to new posts.")
    .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
    .addChannelOption((o) =>
      o
        .setName("channel")
        .setDescription("Channel to set as a forum channel.")
        .addChannelTypes(ChannelType.GuildForum)
        .setRequired(false)
    )
    .addRoleOption((o) =>
      o.setName("role").setDescription("Role to set (optional).").setRequired(false)
    ),

  async execute(interaction) {
    const channel = interaction.options.getChannel("channel");
    const role = interaction.options.getRole("role");
    const parts = [];

    if (!channel) {
      await deleteGuildVar(interaction.guild.id, "forum_channel");
      parts.push("Removed forum channel from adding admins in new posts!");
    } else {
      await setGuildVar(interaction.guild.id, "forum_channel", channel.id);
      parts.push(`Set ${channel} as forum channel successfully!`);
    }

    if (role) {
      await setGuildVar(interaction.guild.id, "staff_role", role.id);
      parts.push(`Staff role set to ${role}!`);
    }

    await interaction.reply({ content: parts.join("\n"), flags: MessageFlags.Ephemeral });
  },
};
