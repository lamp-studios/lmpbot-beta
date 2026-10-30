# Storage router: try backends in priority order (Mongo -> Supabase -> Neon -> Turso -> SQLite).
#
# Writes go to the first healthy backend, then the same key is best-effort
# removed from the others so there's a single source of truth. Reads walk the
# same order and return the first hit; list/aggregate reads merge across all
# backends (priority wins on conflicts) so nothing is lost if data fragmented
# during an outage.

import asyncio
import time

from utils.backends.mongo import mongo
from utils.backends.neon import neon
from utils.backends.sqlite import sqlite
from utils.backends.supabase import supabase
from utils.backends.turso import turso

# priority order; sqlite is always last (last-resort local fallback)
ALL = [mongo, supabase, neon, turso, sqlite]


def _active():
    return [b for b in ALL if b.available()]


def _str(value) -> str:
    """Stored values are always strings; booleans are written the way JavaScript wrote them."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


async def init_storage():
    active_names = []
    for b in ALL:
        try:
            if await b.init():
                active_names.append(b.name)
        except Exception as err:
            print(f"[db] {b.name} init failed: {err}")
    if not active_names:
        print("[db] no storage backends active!")
    else:
        print(f"[db] storage backends active: {' -> '.join(active_names)}")
    return active_names


# --- generic routing helpers ---


async def _swallow(coro):
    try:
        await coro
    except Exception:
        pass


async def _write_then_dedup(write_fn, delete_fn):
    backends = _active()
    last_err = None
    for b in backends:
        try:
            await write_fn(b)
            # drop stale copies elsewhere so reads are unambiguous
            await asyncio.gather(*(_swallow(delete_fn(x)) for x in backends if x is not b))
            return
        except Exception as err:
            last_err = err
            print(f"[db] {b.name} write failed, trying next: {err}")
    raise last_err or RuntimeError("no storage backend available")


async def _delete_everywhere(delete_fn):
    await asyncio.gather(*(_swallow(delete_fn(b)) for b in _active()))


async def _read_first(read_fn):
    for b in _active():
        try:
            v = await read_fn(b)
            if v is not None:
                return v
        except Exception as err:
            print(f"[db] {b.name} read failed, trying next: {err}")
    return None


async def _merge_by_key(read_fn, key_of):
    """Merge list rows across backends, first backend wins on key collisions."""
    seen = {}
    for b in _active():
        try:
            for row in await read_fn(b):
                k = key_of(row)
                if k not in seen:
                    seen[k] = row
        except Exception as err:
            print(f"[db] {b.name} read failed, skipping: {err}")
    return list(seen.values())


# -------------------------
# GUILD VARS
# -------------------------


async def get_guild_var(guild_id, key, default=None):
    g = str(guild_id)
    v = await _read_first(lambda b: b.get_guild_var(g, key))
    return v if v is not None else default


async def set_guild_var(guild_id, key, value):
    g = str(guild_id)
    val = _str(value)
    await _write_then_dedup(
        lambda b: b.set_guild_var(g, key, val),
        lambda b: b.delete_guild_var(g, key),
    )


async def delete_guild_var(guild_id, key):
    g = str(guild_id)
    await _delete_everywhere(lambda b: b.delete_guild_var(g, key))


async def search_guild_var(key):
    """Every guild row that has `key` set, as [{"guild_id", "value"}]."""
    return await _merge_by_key(lambda b: b.search_guild_var(key), lambda row: row["guild_id"])


# -------------------------
# MEMBER VARS
# -------------------------


async def get_member_var(guild_id, member_id, key, default=None):
    g = str(guild_id)
    m = str(member_id)
    v = await _read_first(lambda b: b.get_member_var(g, m, key))
    return v if v is not None else default


async def set_member_var(guild_id, member_id, key, value):
    g = str(guild_id)
    m = str(member_id)
    val = _str(value)
    await _write_then_dedup(
        lambda b: b.set_member_var(g, m, key, val),
        lambda b: b.delete_member_var(g, m, key),
    )


async def delete_member_var(guild_id, member_id, key):
    g = str(guild_id)
    m = str(member_id)
    await _delete_everywhere(lambda b: b.delete_member_var(g, m, key))


async def search_member_var(key):
    """Every member row across guilds that has `key` set (e.g. all stored birthdays)."""
    return await _merge_by_key(
        lambda b: b.search_member_var(key),
        lambda row: f"{row['guild_id']}:{row['member_id']}",
    )


# -------------------------
# USER FACTS
# -------------------------


async def set_user_fact(guild_id, user_id, key, value):
    g = str(guild_id)
    u = str(user_id)
    val = _str(value)
    await _write_then_dedup(
        lambda b: b.set_user_fact(g, u, key, val),
        lambda b: b.delete_user_fact(g, u, key),
    )


async def get_user_facts(guild_id, user_id):
    g = str(guild_id)
    u = str(user_id)
    rows = await _merge_by_key(lambda b: b.get_user_facts(g, u), lambda row: row["key"])
    return {r["key"]: r["value"] for r in rows}


# -------------------------
# CHAT MEMORY
# -------------------------


async def add_chat_memory(guild_id, channel_id, user_id, role, content):
    g = str(guild_id)
    c = str(channel_id)
    u = str(user_id)
    ts = int(time.time() * 1000)

    last_err = None
    for b in _active():
        try:
            await b.add_chat_memory(g, c, u, role, content, ts)
            return
        except Exception as err:
            last_err = err
            print(f"[db] {b.name} chat write failed, trying next: {err}")
    raise last_err or RuntimeError("no storage backend available")


async def get_chat_memory(guild_id, channel_id, user_id, limit=10):
    g = str(guild_id)
    c = str(channel_id)
    u = str(user_id)

    rows = []
    for b in _active():
        try:
            rows.extend(await b.get_chat_memory(g, c, u, limit))
        except Exception as err:
            print(f"[db] {b.name} chat read failed, skipping: {err}")

    # oldest -> newest, then keep the most recent `limit` (newest last)
    rows.sort(key=lambda r: r["ts"])
    return [{"role": r["role"], "content": r["content"]} for r in rows[-limit:]]


# -------------------------
# USER ERASURE
# -------------------------

# user id -> when their data was last wiped (ms), so a chatbot reply that was
# already in flight knows not to write anything back for them
_erased_at: dict[str, int] = {}


def erased_since(user_id, since: int) -> bool:
    """True if the user's data was wiped at or after `since` (epoch ms)."""
    at = _erased_at.get(str(user_id))
    return at is not None and at >= since


async def delete_user_data(user_id):
    """
    Delete every chat_memory, user_facts and member_vars row for one user, in
    every guild and every backend. guild_vars only holds server settings, so it
    is left alone. Data may have landed in any backend depending on what was up
    at the time, so all of them are wiped, and one failing doesn't stop the rest.

    Returns one dict per backend: {"backend", "status": "ok" | "failed" | "inactive",
    "counts"?: {table: int | None}, "error"?: str}.
    """
    u = str(user_id)
    _erased_at[u] = int(time.time() * 1000)

    async def wipe(b):
        if not b.available():
            return {"backend": b.name, "status": "inactive"}
        try:
            return {"backend": b.name, "status": "ok", "counts": await b.delete_user_data(u)}
        except Exception as err:
            print(f"[db] {b.name} user data delete failed: {err}")
            return {"backend": b.name, "status": "failed", "error": str(err)}

    return await asyncio.gather(*(wipe(b) for b in ALL))
