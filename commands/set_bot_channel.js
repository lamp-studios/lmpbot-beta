import {
  SlashCommandBuilder,
  PermissionFlagsBits,
  ChannelType,
  MessageFlags,
} from "discord.js";
import { getGuildVar, setGuildVar, deleteGuildVar } from "../utils/db.js";

const TRAP_KEY = "dont_talk_channel";
const LOG_KEY = "dont_talk_logging_channel";

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
    )
    .addChannelOption((o) =>
      o
        .setName("log_channel")
        .setDescription("Channel where detected spambots are logged.")
        .addChannelTypes(ChannelType.GuildText)
        .setRequired(false)
    ),

  async execute(interaction) {
    const guildId = interaction.guild.id;
    const channel = interaction.options.getChannel("channel");
    const logChannel = interaction.options.getChannel("log_channel");

    // no options at all still means "turn the whole thing off"
    if (!channel && !logChannel) {
      await deleteGuildVar(guildId, TRAP_KEY);
      await deleteGuildVar(guildId, LOG_KEY);
      return interaction.reply({
        content: "Removed the dont_talk channel and its log channel.",
        flags: MessageFlags.Ephemeral,
      });
    }

    // either option can be set on its own, so neither path assumes the other ran
    const changes = [];
    if (channel) {
      await setGuildVar(guildId, TRAP_KEY, channel.id);
      changes.push(`dont_talk channel → ${channel}`);
    }
    if (logChannel) {
      await setGuildVar(guildId, LOG_KEY, logChannel.id);
      changes.push(`Log channel → ${logChannel}`);
    }

    // a log channel on its own is valid but does nothing until a trap exists
    const trap = channel ?? (await getGuildVar(guildId, TRAP_KEY));
    const warning = trap
      ? ""
      : "\n\n*No dont_talk channel is set, so nothing will be logged yet. Set one " +
        "with `/set_bot_channel channel:#some-channel`.*";

    return interaction.reply({
      content: `Updated:\n- ${changes.join("\n- ")}${warning}`,
      flags: MessageFlags.Ephemeral,
    });
  },
};
