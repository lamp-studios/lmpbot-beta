// Birthday feature: shared config keys, date helpers, and the daily scheduler.
//
// Dates are intentionally timezone-free. A birthday is stored as a bare
// "DD/MM" string and compared against the bot host's local date, so a server
// running in one place announces on that day's local calendar date.

import { PermissionFlagsBits } from "discord.js";
import {
  getGuildVar,
  setGuildVar,
  searchMemberVar,
} from "./db.js";

// guild-var keys, grouped so the command and scheduler can't drift apart.
export const KEYS = {
  enabled: "birthday_enabled",
  role: "birthday_role",
  channel: "birthday_channel",
  message: "birthday_message",
  pingRole: "birthday_ping_role",
  pingEnabled: "birthday_ping_enabled",
  setChannel: "birthday_set_channel",
  lastRun: "birthday_last_run",
};

export const MEMBER_KEY = "birthday";

export const DEFAULT_MESSAGE = "🎉 Happy birthday {user}! 🎂";

const DAYS_IN_MONTH = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

/**
 * Parse loose user input ("30/01", "30/1", "3/1") into a canonical zero-padded
 * "DD/MM" string, or null if it isn't a valid day/month. 29/02 is allowed.
 */
export function parseDate(input) {
  const m = String(input).trim().match(/^(\d{1,2})\s*\/\s*(\d{1,2})$/);
  if (!m) return null;
  const day = Number(m[1]);
  const month = Number(m[2]);
  if (month < 1 || month > 12) return null;
  if (day < 1 || day > DAYS_IN_MONTH[month - 1]) return null;
  return `${String(day).padStart(2, "0")}/${String(month).padStart(2, "0")}`;
}

/** Today's date as "DD/MM" in the host's local time. */
export function todayKey(now = new Date()) {
  return `${String(now.getDate()).padStart(2, "0")}/${String(now.getMonth() + 1).padStart(2, "0")}`;
}

/** Local calendar day as "YYYY-MM-DD"; used to run the scan once per day. */
function dateStamp(now = new Date()) {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(
    now.getDate()
  ).padStart(2, "0")}`;
}

/** Read the whole birthday config for a guild in one shot. */
export async function getConfig(guildId) {
  const [enabled, role, channel, message, pingRole, pingEnabled, setChannel] = await Promise.all([
    getGuildVar(guildId, KEYS.enabled),
    getGuildVar(guildId, KEYS.role),
    getGuildVar(guildId, KEYS.channel),
    getGuildVar(guildId, KEYS.message),
    getGuildVar(guildId, KEYS.pingRole),
    getGuildVar(guildId, KEYS.pingEnabled),
    getGuildVar(guildId, KEYS.setChannel),
  ]);
  return {
    enabled: enabled === "true",
    roleId: role,
    channelId: channel,
    message: message || DEFAULT_MESSAGE,
    pingRoleId: pingRole,
    pingEnabled: pingEnabled === "true",
    setChannelId: setChannel,
  };
}

/** Fill placeholders in a custom announcement message. */
export function renderMessage(template, member) {
  return (template || DEFAULT_MESSAGE)
    .replaceAll("{user}", member.toString())
    .replaceAll("{mention}", member.toString())
    .replaceAll("{name}", member.displayName ?? member.user.username);
}

const CHECK_INTERVAL_MS = 30 * 60 * 1000; // re-check every 30 minutes
const ANNOUNCE_HOUR = 8; // don't announce before 08:00 host-local time

/**
 * Announce today's birthdays for one guild and reconcile the birthday role
 * (grant to today's people, revoke from everyone else who still has it).
 */
async function processGuild(guild, birthdaysByMember, today) {
  const cfg = await getConfig(guild.id);
  if (!cfg.enabled) return;

  const role = cfg.roleId ? guild.roles.cache.get(cfg.roleId) : null;
  const channel = cfg.channelId ? guild.channels.cache.get(cfg.channelId) : null;

  const celebrantIds = new Set(
    [...birthdaysByMember].filter(([, date]) => date === today).map(([id]) => id)
  );

  // Revoke a stale birthday role before granting today's, so yesterday's
  // celebrants don't keep it. Only touches members who currently hold it.
  if (role) {
    for (const member of role.members.values()) {
      if (!celebrantIds.has(member.id)) {
        await member.roles.remove(role).catch(() => {});
      }
    }
  }

  for (const memberId of celebrantIds) {
    const member = await guild.members.fetch(memberId).catch(() => null);
    if (!member) continue;

    if (role) await member.roles.add(role).catch(() => {});

    if (channel && channel.isTextBased()) {
      const ping =
        cfg.pingEnabled && cfg.pingRoleId ? `<@&${cfg.pingRoleId}> ` : "";
      await channel
        .send({
          content: ping + renderMessage(cfg.message, member),
          allowedMentions: {
            users: [member.id],
            roles: ping ? [cfg.pingRoleId] : [],
          },
        })
        .catch(() => {});
    }
  }
}

async function runScan(client) {
  const now = new Date();
  if (now.getHours() < ANNOUNCE_HOUR) return;

  const stamp = dateStamp(now);
  const today = todayKey(now);

  // group every stored birthday by guild so we hit the DB once per scan
  const byGuild = new Map();
  for (const row of await searchMemberVar(MEMBER_KEY)) {
    if (!byGuild.has(row.guildId)) byGuild.set(row.guildId, new Map());
    byGuild.get(row.guildId).set(row.memberId, row.value);
  }

  for (const guild of client.guilds.cache.values()) {
    // once per day per guild, even across restarts
    const lastRun = await getGuildVar(guild.id, KEYS.lastRun);
    if (lastRun === stamp) continue;

    const cfg = await getConfig(guild.id);
    if (!cfg.enabled) continue;

    await setGuildVar(guild.id, KEYS.lastRun, stamp);
    try {
      await processGuild(guild, byGuild.get(guild.id) ?? new Map(), today);
    } catch (err) {
      console.warn(`[birthdays] scan failed for guild ${guild.id}: ${err?.message ?? err}`);
    }
  }
}

/** Start the once-a-day birthday scan loop. */
export function startBirthdayScheduler(client) {
  const tick = () => runScan(client).catch((err) => console.warn(`[birthdays] ${err}`));
  tick();
  setInterval(tick, CHECK_INTERVAL_MS);
  console.log("[birthdays] scheduler started");
}

/** True if the interacting member may change server-wide birthday settings. */
export function isAdmin(interaction) {
  return interaction.memberPermissions?.has(PermissionFlagsBits.Administrator) ?? false;
}
