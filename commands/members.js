import { SlashCommandBuilder, MessageFlags } from "discord.js";
import { getMemberVar } from "../utils/db.js";

export default {
  data: new SlashCommandBuilder()
    .setName("members")
    .setDescription("See all verified members."),

  async execute(interaction) {
    await interaction.deferReply({ flags: MessageFlags.Ephemeral });

    const members = await interaction.guild.members.fetch();

    const verified = [];
    for (const member of members.values()) {
      if ((await getMemberVar(interaction.guild.id, member.id, "is_verified")) === "true") {
        verified.push(member.toString());
      }
    }

    const text = verified.length ? verified.join("\n") : "None";
    await interaction.followUp({ content: text, allowedMentions: { parse: [] } });
  },
};
