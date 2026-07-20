// Storage router: try backends in priority order (Mongo -> Supabase -> SQLite).
//
// Writes go to the first healthy backend, then the same key is best-effort
// removed from the others so there's a single source of truth. Reads walk the
// same order and return the first hit; list/aggregate reads merge across all
// backends (priority wins on conflicts) so nothing is lost if data fragmented
// during an outage.

import { mongo } from "./backends/mongo.js";
import { supabase } from "./backends/supabase.js";
import { sqlite } from "./backends/sqlite.js";

// priority order; sqlite is always last (last-resort local fallback)
const ALL = [mongo, supabase, sqlite];

function active() {
  return ALL.filter((b) => b.available());
}

export async function initStorage() {
  const activeNames = [];
  for (const b of ALL) {
    try {
      if (await b.init()) activeNames.push(b.name);
    } catch (err) {
      console.warn(`[db] ${b.name} init failed: ${err?.message ?? err}`);
    }
  }
  if (activeNames.length === 0) console.warn("[db] no storage backends active!");
  else console.log(`[db] storage backends active: ${activeNames.join(" -> ")}`);
  return activeNames;
}

// --- generic routing helpers ---

async function writeThenDedup(writeFn, deleteFn) {
  const list = active();
  let lastErr;
  for (const b of list) {
    try {
      await writeFn(b);
      // drop stale copies elsewhere so reads are unambiguous
      await Promise.allSettled(list.filter((x) => x !== b).map((x) => deleteFn(x).catch(() => {})));
      return;
    } catch (err) {
      lastErr = err;
      console.warn(`[db] ${b.name} write failed, trying next: ${err?.message ?? err}`);
    }
  }
  throw lastErr ?? new Error("no storage backend available");
}

async function deleteEverywhere(deleteFn) {
  await Promise.allSettled(active().map((b) => deleteFn(b).catch(() => {})));
}

async function readFirst(readFn) {
  for (const b of active()) {
    try {
      const v = await readFn(b);
      if (v !== null && v !== undefined) return v;
    } catch (err) {
      console.warn(`[db] ${b.name} read failed, trying next: ${err?.message ?? err}`);
    }
  }
  return null;
}

// merge list rows across backends, first backend wins on key collisions
async function mergeByKey(readFn, keyOf) {
  const seen = new Map();
  for (const b of active()) {
    try {
      for (const row of await readFn(b)) {
        const k = keyOf(row);
        if (!seen.has(k)) seen.set(k, row);
      }
    } catch (err) {
      console.warn(`[db] ${b.name} read failed, skipping: ${err?.message ?? err}`);
    }
  }
  return [...seen.values()];
}

// -------------------------
// GUILD VARS
// -------------------------

export async function getGuildVar(guildId, key, def = null) {
  const g = String(guildId);
  const v = await readFirst((b) => b.getGuildVar(g, key));
  return v ?? def;
}

export async function setGuildVar(guildId, key, value) {
  const g = String(guildId);
  const val = String(value);
  await writeThenDedup(
    (b) => b.setGuildVar(g, key, val),
    (b) => b.deleteGuildVar(g, key)
  );
}

export async function deleteGuildVar(guildId, key) {
  const g = String(guildId);
  await deleteEverywhere((b) => b.deleteGuildVar(g, key));
}

export async function searchGuildVar(key) {
  return mergeByKey(
    (b) => b.searchGuildVar(key),
    (row) => row.guildId
  );
}

// -------------------------
// MEMBER VARS
// -------------------------

export async function getMemberVar(guildId, memberId, key, def = null) {
  const g = String(guildId);
  const m = String(memberId);
  const v = await readFirst((b) => b.getMemberVar(g, m, key));
  return v ?? def;
}

export async function setMemberVar(guildId, memberId, key, value) {
  const g = String(guildId);
  const m = String(memberId);
  const val = String(value);
  await writeThenDedup(
    (b) => b.setMemberVar(g, m, key, val),
    (b) => b.deleteMemberVar(g, m, key)
  );
}

export async function deleteMemberVar(guildId, memberId, key) {
  const g = String(guildId);
  const m = String(memberId);
  await deleteEverywhere((b) => b.deleteMemberVar(g, m, key));
}

// Every member row across guilds that has `key` set (e.g. all stored birthdays).
export async function searchMemberVar(key) {
  return mergeByKey(
    (b) => b.searchMemberVar(key),
    (row) => `${row.guildId}:${row.memberId}`
  );
}

// -------------------------
// USER FACTS
// -------------------------

export async function setUserFact(guildId, userId, key, value) {
  const g = String(guildId);
  const u = String(userId);
  const val = String(value);
  await writeThenDedup(
    (b) => b.setUserFact(g, u, key, val),
    (b) => b.deleteUserFact(g, u, key)
  );
}

export async function getUserFacts(guildId, userId) {
  const g = String(guildId);
  const u = String(userId);
  const rows = await mergeByKey(
    (b) => b.getUserFacts(g, u),
    (row) => row.key
  );
  return Object.fromEntries(rows.map((r) => [r.key, r.value]));
}

// -------------------------
// CHAT MEMORY
// -------------------------

export async function addChatMemory(guildId, channelId, userId, role, content) {
  const g = String(guildId);
  const c = String(channelId);
  const u = String(userId);
  const ts = Date.now();

  let lastErr;
  for (const b of active()) {
    try {
      await b.addChatMemory(g, c, u, role, content, ts);
      return;
    } catch (err) {
      lastErr = err;
      console.warn(`[db] ${b.name} chat write failed, trying next: ${err?.message ?? err}`);
    }
  }
  throw lastErr ?? new Error("no storage backend available");
}

export async function getChatMemory(guildId, channelId, userId, limit = 10) {
  const g = String(guildId);
  const c = String(channelId);
  const u = String(userId);

  const all = [];
  for (const b of active()) {
    try {
      all.push(...(await b.getChatMemory(g, c, u, limit)));
    } catch (err) {
      console.warn(`[db] ${b.name} chat read failed, skipping: ${err?.message ?? err}`);
    }
  }

  // oldest -> newest, then keep the most recent `limit` (newest last)
  all.sort((a, b) => a.ts - b.ts);
  return all.slice(-limit).map(({ role, content }) => ({ role, content }));
}
