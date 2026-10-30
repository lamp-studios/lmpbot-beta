# Turso (hosted libSQL) backend, over Turso's HTTP pipeline API. No client
# library: the API is one endpoint, and the official Python client is a native
# build that has no wheels for some Raspberry Pi setups.
#
# The schema is the same as the local SQLite fallback, so rows can move between
# the two without any conversion.

import aiohttp

from config import config
from utils.backends.timestamps import parse_iso, to_iso

TIMEOUT_S = 10

SCHEMA = [
    "CREATE TABLE IF NOT EXISTS guild_vars ("
    " guild_id TEXT, key TEXT, value TEXT, PRIMARY KEY (guild_id, key))",
    "CREATE TABLE IF NOT EXISTS member_vars ("
    " guild_id TEXT, member_id TEXT, key TEXT, value TEXT, PRIMARY KEY (guild_id, member_id, key))",
    "CREATE TABLE IF NOT EXISTS user_facts ("
    " guild_id TEXT, user_id TEXT, key TEXT, value TEXT, PRIMARY KEY (guild_id, user_id, key))",
    "CREATE TABLE IF NOT EXISTS chat_memory ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT, channel_id TEXT, user_id TEXT,"
    " role TEXT, content TEXT, created_at TEXT)",
]

_url: str | None = None
_session: aiohttp.ClientSession | None = None


def _pipeline_url(raw: str) -> str:
    """libsql://db.turso.io -> https://db.turso.io/v2/pipeline"""
    base = raw.strip().rstrip("/")
    if base.startswith("libsql://"):
        base = "https://" + base[len("libsql://"):]
    return f"{base}/v2/pipeline"


def _arg(value):
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "integer", "value": "1" if value else "0"}
    if isinstance(value, int):
        # libSQL takes integers as strings so 64-bit values survive JSON
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        return {"type": "float", "value": value}
    return {"type": "text", "value": str(value)}


def _cell(cell):
    kind = cell.get("type")
    if kind == "null":
        return None
    if kind == "integer":
        return int(cell["value"])
    return cell.get("value")


async def _execute(*statements):
    """
    Run statements in one pipeline request and return one result per statement:
    {"rows": [dict, ...], "affected": int}. Raises on any statement error, so a
    Turso failure falls through to the next backend like the others do.
    """
    requests = [
        {"type": "execute", "stmt": {"sql": sql, "args": [_arg(a) for a in args]}} for sql, args in statements
    ]
    requests.append({"type": "close"})

    async with _session.post(
        _url,
        json={"requests": requests},
        headers={"Authorization": f"Bearer {config.turso_auth_token}"},
    ) as res:
        text = await res.text()
        if res.status >= 400:
            raise RuntimeError(f"turso: HTTP {res.status}" + (f": {text[:300]}" if text else ""))
        data = await res.json(content_type=None)

    out = []
    for result in data.get("results", [])[: len(statements)]:
        if result.get("type") != "ok":
            message = (result.get("error") or {}).get("message") or "unknown error"
            raise RuntimeError(f"turso: {message}")
        rs = result["response"]["result"]
        names = [c.get("name") for c in rs.get("cols", [])]
        out.append(
            {
                "rows": [dict(zip(names, (_cell(c) for c in row))) for row in rs.get("rows", [])],
                "affected": rs.get("affected_row_count", 0),
            }
        )
    return out


async def _query(sql, *args):
    return (await _execute((sql, args)))[0]


class TursoBackend:
    name = "turso"

    async def init(self) -> bool:
        global _url, _session
        if not config.turso_database_url or not config.turso_auth_token:
            return False

        _url = _pipeline_url(config.turso_database_url)
        _session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=TIMEOUT_S))
        try:
            await _execute(*((sql, ()) for sql in SCHEMA))
        except Exception:
            await _session.close()
            _session = None
            raise
        return True

    def available(self) -> bool:
        return _session is not None

    # --- guild vars ---
    async def get_guild_var(self, guild_id, key):
        rows = (await _query("SELECT value FROM guild_vars WHERE guild_id = ? AND key = ?", guild_id, key))["rows"]
        return rows[0]["value"] if rows else None

    async def set_guild_var(self, guild_id, key, value):
        await _query(
            "INSERT INTO guild_vars (guild_id, key, value) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, key) DO UPDATE SET value = excluded.value",
            guild_id,
            key,
            value,
        )

    async def delete_guild_var(self, guild_id, key):
        await _query("DELETE FROM guild_vars WHERE guild_id = ? AND key = ?", guild_id, key)

    async def search_guild_var(self, key):
        rows = (await _query("SELECT guild_id, value FROM guild_vars WHERE key = ?", key))["rows"]
        return [{"guild_id": r["guild_id"], "value": r["value"]} for r in rows]

    # --- member vars ---
    async def get_member_var(self, guild_id, member_id, key):
        rows = (
            await _query(
                "SELECT value FROM member_vars WHERE guild_id = ? AND member_id = ? AND key = ?",
                guild_id,
                member_id,
                key,
            )
        )["rows"]
        return rows[0]["value"] if rows else None

    async def set_member_var(self, guild_id, member_id, key, value):
        await _query(
            "INSERT INTO member_vars (guild_id, member_id, key, value) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, member_id, key) DO UPDATE SET value = excluded.value",
            guild_id,
            member_id,
            key,
            value,
        )

    async def delete_member_var(self, guild_id, member_id, key):
        await _query(
            "DELETE FROM member_vars WHERE guild_id = ? AND member_id = ? AND key = ?", guild_id, member_id, key
        )

    async def search_member_var(self, key):
        rows = (await _query("SELECT guild_id, member_id, value FROM member_vars WHERE key = ?", key))["rows"]
        return [{"guild_id": r["guild_id"], "member_id": r["member_id"], "value": r["value"]} for r in rows]

    # --- user facts ---
    async def set_user_fact(self, guild_id, user_id, key, value):
        await _query(
            "INSERT INTO user_facts (guild_id, user_id, key, value) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id, key) DO UPDATE SET value = excluded.value",
            guild_id,
            user_id,
            key,
            value,
        )

    async def delete_user_fact(self, guild_id, user_id, key):
        await _query(
            "DELETE FROM user_facts WHERE guild_id = ? AND user_id = ? AND key = ?", guild_id, user_id, key
        )

    async def get_user_facts(self, guild_id, user_id):
        rows = (
            await _query("SELECT key, value FROM user_facts WHERE guild_id = ? AND user_id = ?", guild_id, user_id)
        )["rows"]
        return [{"key": r["key"], "value": r["value"]} for r in rows]

    # --- chat memory ---
    async def add_chat_memory(self, guild_id, channel_id, user_id, role, content, ts):
        await _query(
            "INSERT INTO chat_memory (guild_id, channel_id, user_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            guild_id,
            channel_id,
            user_id,
            role,
            content,
            to_iso(ts),
        )

    async def get_chat_memory(self, guild_id, channel_id, user_id, limit):
        rows = (
            await _query(
                "SELECT role, content, created_at FROM chat_memory "
                "WHERE guild_id = ? AND channel_id = ? AND user_id = ? "
                "ORDER BY created_at DESC LIMIT ?",
                guild_id,
                channel_id,
                user_id,
                limit,
            )
        )["rows"]
        return [{"role": r["role"], "content": r["content"], "ts": parse_iso(r["created_at"])} for r in rows]

    # --- erasure ---
    async def delete_user_data(self, user_id):
        chat, facts, members = await _execute(
            ("DELETE FROM chat_memory WHERE user_id = ?", (user_id,)),
            ("DELETE FROM user_facts WHERE user_id = ?", (user_id,)),
            ("DELETE FROM member_vars WHERE member_id = ?", (user_id,)),
        )
        return {
            "chat_memory": chat["affected"],
            "user_facts": facts["affected"],
            "member_vars": members["affected"],
        }


turso = TursoBackend()
