import { SlashCommandBuilder, PermissionFlagsBits, MessageFlags } from "discord.js";
import { setGuildVar, deleteGuildVar } from "../utils/db.js";

export default {
  data: new SlashCommandBuilder()
    .setName("set_verification_role")
    .setDescription("Set a verification role (required).")
    .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
    .addRoleOption((o) =>
      o.setName("role").setDescription("Role to set as verification role.").setRequired(false)
    ),

  async execute(interaction) {
    const role = interaction.options.getRole("role");
    if (!role) {
      await deleteGuildVar(interaction.guild.id, "verification_role");
      await interaction.reply({ content: "Removed verification role!", flags: MessageFlags.Ephemeral });
    } else {
      await setGuildVar(interaction.guild.id, "verification_role", role.id);
      await interaction.reply({
        content: `Set ${role} as verified role successfully!`,
        flags: MessageFlags.Ephemeral,
      });
    }
  },
};
