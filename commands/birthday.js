import { SlashCommandBuilder, ChannelType, MessageFlags } from "discord.js";
import { setGuildVar, setMemberVar } from "../utils/db.js";
import {
  KEYS,
  MEMBER_KEY,
  DEFAULT_MESSAGE,
  parseDate,
  getConfig,
  isAdmin,
} from "../utils/birthdays.js";

const ADMIN_ONLY = "You need the **Administrator** permission to do that.";

function ephemeral(content) {
  return { content, flags: MessageFlags.Ephemeral };
}

export default {
  data: new SlashCommandBuilder()
    .setName("birthday")
    .setDescription("Birthday announcements and roles.")
    .addSubcommand((s) =>
      s
        .setName("set")
        .setDescription("Set your birthday, e.g. /birthday set 30/01 (day/month).")
        .addStringOption((o) =>
          o.setName("date").setDescription("Your birthday as day/month, e.g. 30/01").setRequired(true)
        )
    )
    .addSubcommand((s) =>
      s
        .setName("settings")
        .setDescription("(Admin) View or change birthday settings. Run with no options to view.")
        .addRoleOption((o) =>
          o.setName("role").setDescription("Role given to a member on their birthday.")
        )
        .addChannelOption((o) =>
          o
            .setName("channel")
            .setDescription("Channel where birthdays are announced.")
            .addChannelTypes(ChannelType.GuildText)
        )
        .addStringOption((o) =>
          o
            .setName("message")
            .setDescription("Custom announcement. Placeholders: {user}, {name}.")
        )
        .addRoleOption((o) =>
          o.setName("ping_role").setDescription("Role to ping in announcements.")
        )
        .addBooleanOption((o) =>
          o.setName("ping").setDescription("Turn the announcement ping on or off.")
        )
        .addChannelOption((o) =>
          o
            .setName("set_channel")
            .setDescription("Channel where members must run /birthday set.")
            .addChannelTypes(ChannelType.GuildText)
        )
    )
    .addSubcommand((s) =>
      s.setName("enable").setDescription("(Admin) Enable the birthday feature.")
    )
    .addSubcommand((s) =>
      s.setName("disable").setDescription("(Admin) Disable the birthday feature.")
    ),

  async execute(interaction) {
    const sub = interaction.options.getSubcommand();
    const guildId = interaction.guild.id;

    if (sub === "set") return setBirthday(interaction, guildId);
    if (sub === "settings") return settings(interaction, guildId);
    if (sub === "enable") return toggle(interaction, guildId, true);
    if (sub === "disable") return toggle(interaction, guildId, false);
  },
};

async function setBirthday(interaction, guildId) {
  const cfg = await getConfig(guildId);
  if (!cfg.enabled) {
    return interaction.reply(ephemeral("The birthday feature is currently disabled on this server."));
  }
  if (cfg.setChannelId && interaction.channel.id !== cfg.setChannelId) {
    return interaction.reply(ephemeral(`Please use <#${cfg.setChannelId}> to set your birthday.`));
  }

  const raw = interaction.options.getString("date");
  const date = parseDate(raw);
  if (!date) {
    return interaction.reply(
      ephemeral(`\`${raw}\` isn't a valid day/month. Try something like \`30/01\`.`)
    );
  }

  await setMemberVar(guildId, interaction.user.id, MEMBER_KEY, date);
  return interaction.reply(ephemeral(`Your birthday is set to **${date}** (day/month). 🎂`));
}

async function toggle(interaction, guildId, enabled) {
  if (!isAdmin(interaction)) return interaction.reply(ephemeral(ADMIN_ONLY));
  await setGuildVar(guildId, KEYS.enabled, enabled ? "true" : "false");
  return interaction.reply(
    ephemeral(enabled ? "Birthday feature **enabled**." : "Birthday feature **disabled**.")
  );
}

async function settings(interaction, guildId) {
  if (!isAdmin(interaction)) return interaction.reply(ephemeral(ADMIN_ONLY));

  const role = interaction.options.getRole("role");
  const channel = interaction.options.getChannel("channel");
  const message = interaction.options.getString("message");
  const pingRole = interaction.options.getRole("ping_role");
  const ping = interaction.options.getBoolean("ping");
  const setChannel = interaction.options.getChannel("set_channel");

  const noChanges =
    role === null &&
    channel === null &&
    message === null &&
    pingRole === null &&
    ping === null &&
    setChannel === null;

  if (noChanges) return interaction.reply(await settingsSummary(guildId));

  const changes = [];
  if (role) {
    await setGuildVar(guildId, KEYS.role, role.id);
    changes.push(`Birthday role → ${role}`);
  }
  if (channel) {
    await setGuildVar(guildId, KEYS.channel, channel.id);
    changes.push(`Announcement channel → ${channel}`);
  }
  if (message !== null) {
    await setGuildVar(guildId, KEYS.message, message);
    changes.push("Custom message updated");
  }
  if (pingRole) {
    await setGuildVar(guildId, KEYS.pingRole, pingRole.id);
    await setGuildVar(guildId, KEYS.pingEnabled, "true");
    changes.push(`Ping role → ${pingRole} (ping on)`);
  }
  if (ping !== null) {
    await setGuildVar(guildId, KEYS.pingEnabled, ping ? "true" : "false");
    changes.push(`Announcement ping → ${ping ? "on" : "off"}`);
  }
  if (setChannel) {
    await setGuildVar(guildId, KEYS.setChannel, setChannel.id);
    changes.push(`/birthday set channel → ${setChannel}`);
  }

  return interaction.reply(ephemeral(`Updated:\n- ${changes.join("\n- ")}`));
}

async function settingsSummary(guildId) {
  const cfg = await getConfig(guildId);
  const roleOrNone = (id) => (id ? `<@&${id}>` : "*none*");
  const chOrNone = (id) => (id ? `<#${id}>` : "*none*");

  const lines = [
    "# Birthday settings",
    `- Feature: **${cfg.enabled ? "enabled" : "disabled"}**`,
    `- Birthday role: ${roleOrNone(cfg.roleId)}`,
    `- Announcement channel: ${chOrNone(cfg.channelId)}`,
    `- Ping role: ${roleOrNone(cfg.pingRoleId)} (ping ${cfg.pingEnabled ? "on" : "off"})`,
    `- /birthday set channel: ${cfg.setChannelId ? chOrNone(cfg.setChannelId) : "*anywhere*"}`,
    `- Message: ${cfg.message === DEFAULT_MESSAGE ? "*default*" : "`" + cfg.message + "`"}`,
  ];
  return ephemeral(lines.join("\n"));
}
