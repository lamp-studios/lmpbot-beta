// Server lockdown: hide every channel from a role except one, and be able to put
// it all back.
//
// The role defaults to @everyone but can be any role, because plenty of servers
// gate access behind a "member" role that grants View Channel explicitly — a
// deny on @everyone does nothing to those people. Each locked role is recorded
// on its own, so a second /lockdown can cover another role without disturbing
// the first, and one /undolockdown lifts the lot.
//
// Only the target role's "View Channel" bit is touched, and only on channels the
// bot can already manage, so every other overwrite survives untouched. What that
// bit was per channel is stored as JSON in a guild var, which is what makes the
// undo exact: a channel that was explicitly allowed goes back to allowed, a
// neutral one goes back to neutral. Channels where the role was *already* denied
// are skipped entirely, so an undo can never open up a private channel that the
// lockdown had nothing to do with.

import { OverwriteType, PermissionFlagsBits } from "discord.js";
import { getGuildVar, setGuildVar, deleteGuildVar } from "./db.js";

export const STATE_KEY = "lockdown_state";

// the target role's View Channel bit as stored per channel
const ALLOW = "a";
const DENY = "d";
const NEUTRAL = "n";

const TO_VALUE = { [ALLOW]: true, [DENY]: false, [NEUTRAL]: null };

// How many channels are edited at once. Overwrite edits are rate limited per
// channel rather than per guild, so a small fan-out is far quicker than going
// one at a time without pushing at the global limit on a big server.
const BATCH = 5;

const VERSION = 2;

/**
 * Stored lockdown state:
 * {
 *   v: 2,
 *   at: epoch ms,
 *   by: user id,
 *   targets: [
 *     {
 *       roleId,
 *       exceptionId: channel id | null,
 *       channels: { [channelId]: "a" | "d" | "n" },  // bit to restore
 *     },
 *   ],
 *   botPins: { [channelId]: "new" | "bit" }          // overwrites we added for ourselves
 * }
 */

/** Bring the pre-role state shape forward; it was always an @everyone lockdown. */
function normalize(state, guildId) {
  if (!state || Array.isArray(state.targets)) return state;
  return {
    ...state,
    v: VERSION,
    // the @everyone role always shares the guild's id
    targets: [
      {
        roleId: String(guildId),
        exceptionId: state.exceptionId ?? null,
        channels: state.channels ?? {},
      },
    ],
    botPins: state.botPins ?? {},
  };
}

export async function readLockdown(guildId) {
  const raw = await getGuildVar(guildId, STATE_KEY);
  if (!raw) return null;
  try {
    return normalize(JSON.parse(raw), guildId);
  } catch (err) {
    console.warn(`[lockdown] unreadable state for guild ${guildId}: ${err?.message ?? err}`);
    return null;
  }
}

export async function saveLockdown(guildId, state) {
  await setGuildVar(guildId, STATE_KEY, JSON.stringify(state));
}

export async function clearLockdown(guildId) {
  await deleteGuildVar(guildId, STATE_KEY);
}

/** Ids of every role a lockdown is currently holding down. */
export function lockedRoleIds(state) {
  return (state?.targets ?? []).map((t) => t.roleId);
}

/** Every channel a lockdown can touch. Threads have no overwrites of their own. */
function lockable(guild) {
  return [...guild.channels.cache.values()].filter((c) => c && !c.isThread());
}

/** One role's View Channel bit on one channel, right now. */
function viewState(channel, roleId) {
  const overwrite = channel.permissionOverwrites.cache.get(roleId);
  if (!overwrite) return NEUTRAL;
  if (overwrite.allow.has(PermissionFlagsBits.ViewChannel)) return ALLOW;
  if (overwrite.deny.has(PermissionFlagsBits.ViewChannel)) return DENY;
  return NEUTRAL;
}

/** Whether the bot can edit this channel's overwrites at all. */
export function manageable(channel, me) {
  const perms = channel.permissionsFor(me);
  return Boolean(
    perms?.has(PermissionFlagsBits.ViewChannel) && perms.has(PermissionFlagsBits.ManageRoles)
  );
}

/**
 * Whether the bot would still see a channel once `target` is denied there.
 * A deny reaches the bot through any role it holds, so when the bot is in the
 * role being locked down it needs an administrator role or an allow of its own,
 * or it loses access to the very channel it has to undo later.
 */
function botKeepsAccess(channel, me, target) {
  if (me.permissions.has(PermissionFlagsBits.Administrator)) return true;
  // includes @everyone, so this covers the default target too
  if (!me.roles.cache.has(target.id)) return true;

  const mine = new Set([me.id, ...me.roles.cache.keys()]);
  mine.delete(target.id);

  for (const overwrite of channel.permissionOverwrites.cache.values()) {
    if (mine.has(overwrite.id) && overwrite.allow.has(PermissionFlagsBits.ViewChannel)) return true;
  }
  return false;
}

/**
 * Give the bot an explicit View Channel allow so the deny about to land can't
 * lock it out. Returns how to clean it up again: "new" if the whole overwrite is
 * ours to delete, "bit" if we only added to one that was already there.
 */
async function pinBotAccess(channel, me, reason) {
  const existed = channel.permissionOverwrites.cache.has(me.id);
  await channel.permissionOverwrites.edit(
    me,
    { ViewChannel: true },
    { reason, type: OverwriteType.Member }
  );
  return existed ? "bit" : "new";
}

async function inBatches(items, fn) {
  for (let i = 0; i < items.length; i += BATCH) {
    await Promise.all(items.slice(i, i + BATCH).map((item) => fn(item)));
  }
}

/** A few channel names for a report, trimmed so a big server can't overflow it. */
export function nameList(channels, max = 5) {
  const shown = channels.slice(0, max).map((c) => `#${c.name}`).join(", ");
  const left = channels.length - max;
  return left > 0 ? `${shown} and ${left} more` : shown;
}

/**
 * Hide every channel from `role` (default @everyone), apart from `exception`.
 *
 * `previous` is an existing lockdown to fold this one into, so a second role can
 * be locked down without losing the first role's saved permissions.
 *
 * Returns `{ state, hidden, alreadyHidden, skipped, failed, exceptionWasHidden }`.
 * `state` is null when nothing was changed, so no lockdown gets recorded.
 */
export async function applyLockdown(guild, { role, exception, user, reason, previous = null }) {
  const me = guild.members.me ?? (await guild.members.fetchMe());
  const target = role ?? guild.roles.everyone;

  const record = { roleId: target.id, exceptionId: exception?.id ?? null, channels: {} };
  const pins = {};

  const targets = [];
  const skipped = [];
  let alreadyHidden = 0;

  for (const channel of lockable(guild)) {
    if (channel.id === exception?.id) continue;
    if (!manageable(channel, me)) {
      skipped.push(channel);
      continue;
    }
    // already invisible to the role: leave it be, so undoing can't reveal it
    if (viewState(channel, target.id) === DENY) {
      alreadyHidden++;
      continue;
    }
    targets.push(channel);
  }

  const hidden = [];
  const failed = [];

  await inBatches(targets, async (channel) => {
    const before = viewState(channel, target.id);
    try {
      if (!botKeepsAccess(channel, me, target)) {
        // recorded before the deny lands, so a half-done channel still cleans up
        pins[channel.id] = await pinBotAccess(channel, me, reason);
      }
      await channel.permissionOverwrites.edit(
        target,
        { ViewChannel: false },
        { reason, type: OverwriteType.Role }
      );
      record.channels[channel.id] = before;
      hidden.push(channel);
    } catch (err) {
      console.warn(`[lockdown] ${guild.id}/${channel.id} failed: ${err?.message ?? err}`);
      failed.push(channel);
    }
  });

  // The exception goes last and is allowed explicitly rather than left alone, so
  // it is visible whatever it inherited before.
  let exceptionWasHidden = false;
  if (exception) {
    const before = viewState(exception, target.id);
    exceptionWasHidden = before === DENY;
    if (before !== ALLOW) {
      try {
        await exception.permissionOverwrites.edit(
          target,
          { ViewChannel: true },
          { reason, type: OverwriteType.Role }
        );
        record.channels[exception.id] = before;
      } catch (err) {
        console.warn(`[lockdown] ${guild.id} exception failed: ${err?.message ?? err}`);
        failed.push(exception);
      }
    }
  }

  const touched = Object.keys(record.channels).length + Object.keys(pins).length;
  const state = touched
    ? {
        v: VERSION,
        at: Date.now(),
        by: user.id,
        targets: [...(previous?.targets ?? []), record],
        // an earlier pin is the one that created the overwrite, so it wins
        botPins: { ...pins, ...(previous?.botPins ?? {}) },
      }
    : null;

  return { state, target, hidden, alreadyHidden, skipped, failed, exceptionWasHidden };
}

/**
 * Put back every View Channel bit the lockdown changed, for every role it holds.
 *
 * Returns `{ restored, roles, goneRoles, missing, failed, remaining }`.
 * `remaining` is a trimmed state covering only what failed, so it can be saved
 * and retried instead of leaving channels stuck hidden with nothing left to undo
 * them with.
 */
export async function restoreLockdown(guild, state, reason) {
  const me = guild.members.me ?? (await guild.members.fetchMe());

  const restored = [];
  const missing = [];
  const failed = [];
  const roles = [];
  const goneRoles = [];
  const targetsLeft = [];
  const stuck = new Set();

  for (const target of state.targets ?? []) {
    const role = guild.roles.cache.get(target.roleId);
    if (!role) {
      // Discord drops a role's overwrites along with the role itself
      goneRoles.push(target.roleId);
      continue;
    }
    roles.push(role);

    const leftover = {};
    await inBatches(Object.entries(target.channels ?? {}), async ([id, before]) => {
      const channel = guild.channels.cache.get(id);
      if (!channel) {
        missing.push(id);
        return;
      }
      try {
        await channel.permissionOverwrites.edit(
          role,
          { ViewChannel: TO_VALUE[before] ?? null },
          { reason, type: OverwriteType.Role }
        );
        restored.push(channel);
      } catch (err) {
        console.warn(`[lockdown] undo ${guild.id}/${id} failed: ${err?.message ?? err}`);
        failed.push(channel);
        leftover[id] = before;
        stuck.add(id);
      }
    });

    if (Object.keys(leftover).length) targetsLeft.push({ ...target, channels: leftover });
  }

  // Our own access comes off only where every role is already back, otherwise a
  // retry would have no way in.
  const pinsLeft = {};

  await inBatches(Object.entries(state.botPins ?? {}), async ([id, kind]) => {
    if (stuck.has(id)) {
      pinsLeft[id] = kind;
      return;
    }
    const channel = guild.channels.cache.get(id);
    if (!channel) return;
    try {
      if (kind === "new") await channel.permissionOverwrites.delete(me, reason);
      else {
        await channel.permissionOverwrites.edit(
          me,
          { ViewChannel: null },
          { reason, type: OverwriteType.Member }
        );
      }
    } catch (err) {
      console.warn(`[lockdown] undo pin ${guild.id}/${id} failed: ${err?.message ?? err}`);
    }
  });

  const remaining = targetsLeft.length
    ? { ...state, targets: targetsLeft, botPins: pinsLeft }
    : null;

  return { restored, roles, goneRoles, missing, failed, remaining };
}
