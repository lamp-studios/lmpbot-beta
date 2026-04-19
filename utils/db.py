import os
import aiosqlite

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "bot.db")


async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_facts (
                guild_id INTEGER,
                user_id INTEGER,
                key TEXT,
                value TEXT,
                PRIMARY KEY (guild_id, user_id, key)
            )
            """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS guild_vars (
                guild_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                PRIMARY KEY (guild_id, key)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS member_vars (
                guild_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                PRIMARY KEY (guild_id, member_id, key)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_memory (
                guild_id INTEGER,
                channel_id INTEGER,
                user_id INTEGER,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await conn.commit()


# -------------------------
# GUILD VARS
# -------------------------

async def get_guild_var(guild_id: int, key: str, default=None) -> str | None:
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            "SELECT value FROM guild_vars WHERE guild_id = ? AND key = ?",
            (guild_id, key),
        )
        row = await cursor.fetchone()
        return row[0] if row else default


async def set_guild_var(guild_id: int, key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO guild_vars (guild_id, key, value) VALUES (?, ?, ?)",
            (guild_id, key, str(value)),
        )
        await conn.commit()


async def delete_guild_var(guild_id: int, key: str):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "DELETE FROM guild_vars WHERE guild_id = ? AND key = ?",
            (guild_id, key),
        )
        await conn.commit()


async def search_guild_var(key: str) -> list[tuple[int, str]]:
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            "SELECT guild_id, value FROM guild_vars WHERE key = ?", (key,)
        )
        return await cursor.fetchall()


# -------------------------
# MEMBER VARS
# -------------------------

async def get_member_var(guild_id: int, member_id: int, key: str, default=None) -> str | None:
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            "SELECT value FROM member_vars WHERE guild_id = ? AND member_id = ? AND key = ?",
            (guild_id, member_id, key),
        )
        row = await cursor.fetchone()
        return row[0] if row else default


async def set_member_var(guild_id: int, member_id: int, key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO member_vars (guild_id, member_id, key, value) VALUES (?, ?, ?, ?)",
            (guild_id, member_id, key, str(value)),
        )
        await conn.commit()
        
async def set_user_fact(guild_id: int, user_id: int, key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO user_facts (guild_id, user_id, key, value) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, key, value)
        )
        await conn.commit()


async def get_user_facts(guild_id: int, user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            "SELECT key, value FROM user_facts WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        )
        rows = await cursor.fetchall()
        return {k: v for k, v in rows}