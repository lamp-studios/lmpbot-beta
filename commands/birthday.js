import { SlashCommandBuilder, ChannelType, MessageFlags } from "discord.js";
import { setGuildVar, setMemberVar } from "../utils/db.js";
import {
  KEYS,
  MEMBER_KEY,
  EPHEMERAL_KEY,
  DEFAULT_MESSAGE,
  parseDate,
  calendarOrder,
  daysUntil,
  getConfig,
  getGuildBirthdays,
  prefersEphemeral,
  isAdmin,
} from "../utils/birthdays.js";

const ADMIN_ONLY = "You need the **Administrator** permission to do that.";
const DISABLED = "The birthday feature is currently disabled on this server.";

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

// leaves room under Discord's 2000-character limit for the overflow note
const MAX_LEN = 1800;

/** Payload for denials and input errors, which stay private whatever the preference. */
function ephemeral(content) {
  return { content, flags: MessageFlags.Ephemeral };
}

/**
 * Payload for successful output: private only if the member asked for that.
 * Mentions are never resolved — a public settings summary would otherwise ping
 * every role it lists.
 */
async function forMember(interaction, content) {
  const priv = await prefersEphemeral(interaction.guild.id, interaction.user.id);
  return {
    content,
    allowedMentions: { parse: [] },
    ...(priv ? { flags: MessageFlags.Ephemeral } : {}),
  };
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
      s.setName("list").setDescription("See everyone's birthday on this server, in calendar order.")
    )
    .addSubcommand((s) =>
      s
        .setName("upcoming")
        .setDescription("See the birthdays coming up soon.")
        .addIntegerOption((o) =>
          o
            .setName("days")
            .setDescription("How many days ahead to look. Defaults to 30.")
            .setMinValue(1)
            .setMaxValue(365)
        )
    )
    .addSubcommand((s) =>
      s
        .setName("visibility")
        .setDescription("Choose who sees your /birthday replies. Run with no option to view.")
        .addStringOption((o) =>
          o
            .setName("mode")
            .setDescription("Keep replies to yourself, or post them in the channel.")
            .addChoices(
              { name: "Only me (ephemeral)", value: "ephemeral" },
              { name: "Everyone (public)", value: "public" }
            )
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
    if (sub === "list") return list(interaction, guildId);
    if (sub === "upcoming") return upcoming(interaction, guildId);
    if (sub === "visibility") return visibility(interaction, guildId);
    if (sub === "settings") return settings(interaction, guildId);
    if (sub === "enable") return toggle(interaction, guildId, true);
    if (sub === "disable") return toggle(interaction, guildId, false);
  },
};

async function setBirthday(interaction, guildId) {
  const cfg = await getConfig(guildId);
  if (!cfg.enabled) return interaction.reply(ephemeral(DISABLED));
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
  return interaction.reply(
    await forMember(interaction, `Your birthday is set to **${date}** (day/month). 🎂`)
  );
}

async function visibility(interaction, guildId) {
  const mode = interaction.options.getString("mode");

  if (mode === null) {
    const priv = await prefersEphemeral(guildId, interaction.user.id);
    return interaction.reply(
      ephemeral(
        `Your \`/birthday\` replies are currently **${
          priv ? "only visible to you" : "posted publicly"
        }**. Change it with \`/birthday visibility\`.`
      )
    );
  }

  await setMemberVar(guildId, interaction.user.id, EPHEMERAL_KEY, mode === "ephemeral" ? "true" : "false");
  return interaction.reply(
    ephemeral(
      mode === "ephemeral"
        ? "Your `/birthday` replies will only be visible to you."
        : "Your `/birthday` replies will now be posted in the channel for everyone to see."
    )
  );
}

/**
 * Resolve stored birthdays to members who are still on the server, newest state
 * from one member fetch. Rows for members who left are dropped.
 */
async function collect(guild) {
  const [stored, members] = await Promise.all([
    getGuildBirthdays(guild.id),
    guild.members.fetch().catch(() => null),
  ]);

  return stored
    .filter((row) => !members || members.has(row.memberId))
    .map((row) => ({ ...row, mention: `<@${row.memberId}>` }));
}

async function list(interaction, guildId) {
  const cfg = await getConfig(guildId);
  if (!cfg.enabled) return interaction.reply(ephemeral(DISABLED));

  const priv = await prefersEphemeral(guildId, interaction.user.id);
  await interaction.deferReply(priv ? { flags: MessageFlags.Ephemeral } : {});

  const entries = await collect(interaction.guild);
  entries.sort((a, b) => calendarOrder(a.date) - calendarOrder(b.date));

  const text = entries.length
    ? renderList(entries)
    : "Nobody has set a birthday yet. Be the first with `/birthday set`.";

  return interaction.editReply({ content: text, allowedMentions: { parse: [] } });
}

async function upcoming(interaction, guildId) {
  const cfg = await getConfig(guildId);
  if (!cfg.enabled) return interaction.reply(ephemeral(DISABLED));

  const window = interaction.options.getInteger("days") ?? 30;
  const priv = await prefersEphemeral(guildId, interaction.user.id);
  await interaction.deferReply(priv ? { flags: MessageFlags.Ephemeral } : {});

  // one `now` for the whole list, so a scan crossing midnight stays consistent
  const now = new Date();
  const entries = (await collect(interaction.guild))
    .map((entry) => ({ ...entry, days: daysUntil(entry.date, now) }))
    .filter((entry) => entry.days !== null && entry.days <= window)
    .sort((a, b) => a.days - b.days || calendarOrder(a.date) - calendarOrder(b.date));

  const text = entries.length
    ? renderUpcoming(entries, window)
    : `No birthdays in the next **${window}** ${window === 1 ? "day" : "days"}. ` +
      "Try `/birthday list` for all of them.";

  return interaction.editReply({ content: text, allowedMentions: { parse: [] } });
}

/** Calendar-ordered birthdays under a heading per month, trimmed to fit one message. */
function renderList(entries) {
  const lines = ["# Birthdays"];
  let used = lines[0].length;
  let month = null;
  let shown = 0;

  for (const entry of entries) {
    const name = MONTHS[Number(entry.date.slice(3)) - 1];
    const chunk = name === month ? [] : [`\n**${name}**`];
    chunk.push(`- \`${entry.date}\` ${entry.mention}`);

    const cost = chunk.join("\n").length + 1;
    if (used + cost > MAX_LEN) break;

    lines.push(...chunk);
    used += cost;
    month = name;
    shown++;
  }

  const left = entries.length - shown;
  if (left > 0) lines.push(`\n*…and ${left} more. Ask again with \`/birthday upcoming\`.*`);
  return lines.join("\n");
}

/** The soonest birthdays first, labelled by how far off they are. */
function renderUpcoming(entries, window) {
  const when = (days) => {
    if (days === 0) return "**today** 🎂";
    if (days === 1) return "**tomorrow**";
    return `in **${days}** days`;
  };

  const lines = ["# Upcoming birthdays", `Next **${window}** ${window === 1 ? "day" : "days"}.`];
  let used = lines.join("\n").length;
  let shown = 0;

  for (const entry of entries) {
    const line = `- \`${entry.date}\` ${entry.mention} — ${when(entry.days)}`;
    if (used + line.length + 1 > MAX_LEN) break;
    lines.push(line);
    used += line.length + 1;
    shown++;
  }

  const left = entries.length - shown;
  if (left > 0) lines.push(`\n*…and ${left} more.*`);
  return lines.join("\n");
}

async function toggle(interaction, guildId, enabled) {
  if (!isAdmin(interaction)) return interaction.reply(ephemeral(ADMIN_ONLY));
  await setGuildVar(guildId, KEYS.enabled, enabled ? "true" : "false");
  return interaction.reply(
    await forMember(
      interaction,
      enabled ? "Birthday feature **enabled**." : "Birthday feature **disabled**."
    )
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

  if (noChanges) return interaction.reply(await forMember(interaction, await settingsSummary(guildId)));

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

  return interaction.reply(await forMember(interaction, `Updated:\n- ${changes.join("\n- ")}`));
}

/** The current guild config as markdown. */
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
  return lines.join("\n");
}
