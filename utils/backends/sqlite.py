import sqlite3
from pathlib import Path

from utils.backends.timestamps import parse_iso, to_iso

DB_PATH = Path(__file__).resolve().parent.parent.parent / "database" / "fallback.db"

_db: sqlite3.Connection | None = None


class SqliteBackend:
    name = "sqlite"

    async def init(self) -> bool:
        global _db
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        # autocommit, so every statement lands on disk straight away
        _db = sqlite3.connect(DB_PATH, isolation_level=None)
        _db.row_factory = sqlite3.Row
        _db.executescript(
            """
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
            """
        )
        return True

    def available(self) -> bool:
        return _db is not None

    # --- guild vars ---
    async def get_guild_var(self, guild_id, key):
        row = _db.execute(
            "SELECT value FROM guild_vars WHERE guild_id = ? AND key = ?", (guild_id, key)
        ).fetchone()
        return row["value"] if row else None

    async def set_guild_var(self, guild_id, key, value):
        _db.execute(
            "INSERT INTO guild_vars (guild_id, key, value) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, key) DO UPDATE SET value = excluded.value",
            (guild_id, key, value),
        )

    async def delete_guild_var(self, guild_id, key):
        _db.execute("DELETE FROM guild_vars WHERE guild_id = ? AND key = ?", (guild_id, key))

    async def search_guild_var(self, key):
        rows = _db.execute("SELECT guild_id, value FROM guild_vars WHERE key = ?", (key,)).fetchall()
        return [{"guild_id": r["guild_id"], "value": r["value"]} for r in rows]

    # --- member vars ---
    async def get_member_var(self, guild_id, member_id, key):
        row = _db.execute(
            "SELECT value FROM member_vars WHERE guild_id = ? AND member_id = ? AND key = ?",
            (guild_id, member_id, key),
        ).fetchone()
        return row["value"] if row else None

    async def set_member_var(self, guild_id, member_id, key, value):
        _db.execute(
            "INSERT INTO member_vars (guild_id, member_id, key, value) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, member_id, key) DO UPDATE SET value = excluded.value",
            (guild_id, member_id, key, value),
        )

    async def delete_member_var(self, guild_id, member_id, key):
        _db.execute(
            "DELETE FROM member_vars WHERE guild_id = ? AND member_id = ? AND key = ?",
            (guild_id, member_id, key),
        )

    async def search_member_var(self, key):
        rows = _db.execute(
            "SELECT guild_id, member_id, value FROM member_vars WHERE key = ?", (key,)
        ).fetchall()
        return [
            {"guild_id": r["guild_id"], "member_id": r["member_id"], "value": r["value"]}
            for r in rows
        ]

    # --- user facts ---
    async def set_user_fact(self, guild_id, user_id, key, value):
        _db.execute(
            "INSERT INTO user_facts (guild_id, user_id, key, value) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id, key) DO UPDATE SET value = excluded.value",
            (guild_id, user_id, key, value),
        )

    async def delete_user_fact(self, guild_id, user_id, key):
        _db.execute(
            "DELETE FROM user_facts WHERE guild_id = ? AND user_id = ? AND key = ?",
            (guild_id, user_id, key),
        )

    async def get_user_facts(self, guild_id, user_id):
        rows = _db.execute(
            "SELECT key, value FROM user_facts WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ).fetchall()
        return [{"key": r["key"], "value": r["value"]} for r in rows]

    # --- chat memory ---
    async def add_chat_memory(self, guild_id, channel_id, user_id, role, content, ts):
        _db.execute(
            "INSERT INTO chat_memory (guild_id, channel_id, user_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, channel_id, user_id, role, content, to_iso(ts)),
        )

    async def get_chat_memory(self, guild_id, channel_id, user_id, limit):
        rows = _db.execute(
            "SELECT role, content, created_at FROM chat_memory "
            "WHERE guild_id = ? AND channel_id = ? AND user_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (guild_id, channel_id, user_id, limit),
        ).fetchall()
        return [
            {"role": r["role"], "content": r["content"], "ts": parse_iso(r["created_at"])}
            for r in rows
        ]

    # --- erasure ---
    async def delete_user_data(self, user_id):
        def wipe(sql):
            return _db.execute(sql, (user_id,)).rowcount

        return {
            "chat_memory": wipe("DELETE FROM chat_memory WHERE user_id = ?"),
            "user_facts": wipe("DELETE FROM user_facts WHERE user_id = ?"),
            "member_vars": wipe("DELETE FROM member_vars WHERE member_id = ?"),
        }


sqlite = SqliteBackend()
