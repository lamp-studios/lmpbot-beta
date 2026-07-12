import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync } from "node:fs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DB_PATH = join(__dirname, "..", "..", "database", "fallback.db");

let db = null;

export const sqlite = {
  name: "sqlite",

  async init() {
    let DatabaseSync;
    try {
      // node:sqlite is built-in from Node 22.5+; import lazily so older
      // runtimes just leave this backend disabled instead of crashing.
      ({ DatabaseSync } = await import("node:sqlite"));
    } catch {
      console.warn("[db] node:sqlite unavailable (needs Node >=22.5); sqlite fallback disabled");
      return false;
    }

    mkdirSync(dirname(DB_PATH), { recursive: true });
    db = new DatabaseSync(DB_PATH);
    db.exec(`
      CREATE TABLE IF NOT EXISTS guild_vars (
        guild_id TEXT, key TEXT, value TEXT,
        PRIMARY KEY (guild_id, key)
      );
      CREATE TABLE IF NOT EXISTS member_vars (
        guild_id TEXT, member_id TEXT, key TEXT, value TEXT,
        PRIMARY KEY (guild_id, member_id, key)
      );
      CREATE TABLE IF NOT EXISTS user_facts (
        guild_id TEXT, user_id TEXT, key TEXT, value TEXT,
        PRIMARY KEY (guild_id, user_id, key)
      );
      CREATE TABLE IF NOT EXISTS chat_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id TEXT, channel_id TEXT, user_id TEXT,
        role TEXT, content TEXT, created_at TEXT
      );
    `);
    return true;
  },

  available() {
    return db !== null;
  },

  // --- guild vars ---
  async getGuildVar(guildId, key) {
    const row = db
      .prepare("SELECT value FROM guild_vars WHERE guild_id = ? AND key = ?")
      .get(guildId, key);
    return row ? row.value : null;
  },
  async setGuildVar(guildId, key, value) {
    db.prepare(
      "INSERT INTO guild_vars (guild_id, key, value) VALUES (?, ?, ?) " +
        "ON CONFLICT(guild_id, key) DO UPDATE SET value = excluded.value"
    ).run(guildId, key, value);
  },
  async deleteGuildVar(guildId, key) {
    db.prepare("DELETE FROM guild_vars WHERE guild_id = ? AND key = ?").run(guildId, key);
  },
  async searchGuildVar(key) {
    return db
      .prepare("SELECT guild_id, value FROM guild_vars WHERE key = ?")
      .all(key)
      .map((r) => ({ guildId: r.guild_id, value: r.value }));
  },

  // --- member vars ---
  async getMemberVar(guildId, memberId, key) {
    const row = db
      .prepare("SELECT value FROM member_vars WHERE guild_id = ? AND member_id = ? AND key = ?")
      .get(guildId, memberId, key);
    return row ? row.value : null;
  },
  async setMemberVar(guildId, memberId, key, value) {
    db.prepare(
      "INSERT INTO member_vars (guild_id, member_id, key, value) VALUES (?, ?, ?, ?) " +
        "ON CONFLICT(guild_id, member_id, key) DO UPDATE SET value = excluded.value"
    ).run(guildId, memberId, key, value);
  },
  async deleteMemberVar(guildId, memberId, key) {
    db.prepare("DELETE FROM member_vars WHERE guild_id = ? AND member_id = ? AND key = ?").run(
      guildId,
      memberId,
      key
    );
  },

  // --- user facts ---
  async setUserFact(guildId, userId, key, value) {
    db.prepare(
      "INSERT INTO user_facts (guild_id, user_id, key, value) VALUES (?, ?, ?, ?) " +
        "ON CONFLICT(guild_id, user_id, key) DO UPDATE SET value = excluded.value"
    ).run(guildId, userId, key, value);
  },
  async deleteUserFact(guildId, userId, key) {
    db.prepare("DELETE FROM user_facts WHERE guild_id = ? AND user_id = ? AND key = ?").run(
      guildId,
      userId,
      key
    );
  },
  async getUserFacts(guildId, userId) {
    return db
      .prepare("SELECT key, value FROM user_facts WHERE guild_id = ? AND user_id = ?")
      .all(guildId, userId)
      .map((r) => ({ key: r.key, value: r.value }));
  },

  // --- chat memory ---
  async addChatMemory(guildId, channelId, userId, role, content, ts) {
    db.prepare(
      "INSERT INTO chat_memory (guild_id, channel_id, user_id, role, content, created_at) " +
        "VALUES (?, ?, ?, ?, ?, ?)"
    ).run(guildId, channelId, userId, role, content, new Date(ts).toISOString());
  },
  async getChatMemory(guildId, channelId, userId, limit) {
    return db
      .prepare(
        "SELECT role, content, created_at FROM chat_memory " +
          "WHERE guild_id = ? AND channel_id = ? AND user_id = ? " +
          "ORDER BY created_at DESC LIMIT ?"
      )
      .all(guildId, channelId, userId, limit)
      .map((r) => ({ role: r.role, content: r.content, ts: Date.parse(r.created_at) }));
  },
};
