# Neon (Lakebase Postgres) backend, over asyncpg.
#
# Queries go through the pooled DATABASE_URL (PgBouncer in transaction mode),
# so asyncpg's prepared-statement cache is turned off: a pooled connection can
# land on a different backend per transaction, and cached statements would fail
# with "prepared statement ... already exists". The one-off schema setup uses the
# direct DATABASE_URL_UNPOOLED when it is set, as Neon recommends for DDL.
#
# The tables match supabase-schema.sql, so the same layout serves both tiers.

from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import asyncpg

from config import config

CONNECT_TIMEOUT_S = 10
COMMAND_TIMEOUT_S = 15

SCHEMA = """
create table if not exists guild_vars (
  guild_id text not null,
  key      text not null,
  value    text,
  primary key (guild_id, key)
);

create table if not exists member_vars (
  guild_id  text not null,
  member_id text not null,
  key       text not null,
  value     text,
  primary key (guild_id, member_id, key)
);

create table if not exists user_facts (
  guild_id text not null,
  user_id  text not null,
  key      text not null,
  value    text,
  primary key (guild_id, user_id, key)
);

create table if not exists chat_memory (
  id         bigint generated always as identity primary key,
  guild_id   text,
  channel_id text,
  user_id    text,
  role       text,
  content    text,
  created_at timestamptz not null default now()
);

create index if not exists chat_memory_lookup
  on chat_memory (guild_id, channel_id, user_id, created_at desc);
"""

# libpq options asyncpg doesn't understand; it would send them on to the server
# as runtime settings, which Postgres rejects
_UNSUPPORTED_PARAMS = {"channel_binding"}

_pool: asyncpg.Pool | None = None


def _dsn(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query) if k not in _UNSUPPORTED_PARAMS]
    return urlunsplit(parts._replace(query=urlencode(query)))


def _deleted(status: str) -> int:
    """Row count from an asyncpg command tag such as "DELETE 3"."""
    try:
        return int(status.rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


class NeonBackend:
    name = "neon"

    async def init(self) -> bool:
        global _pool
        if not config.neon_database_url:
            return False

        direct = await asyncpg.connect(
            _dsn(config.neon_database_url_unpooled or config.neon_database_url),
            timeout=CONNECT_TIMEOUT_S,
            statement_cache_size=0,
        )
        try:
            await direct.execute(SCHEMA)
        finally:
            await direct.close()

        _pool = await asyncpg.create_pool(
            _dsn(config.neon_database_url),
            min_size=1,
            max_size=5,
            timeout=CONNECT_TIMEOUT_S,
            command_timeout=COMMAND_TIMEOUT_S,
            statement_cache_size=0,
            # Neon suspends idle compute, so don't hold connections it will drop
            max_inactive_connection_lifetime=120,
        )
        return True

    def available(self) -> bool:
        return _pool is not None

    # --- guild vars ---
    async def get_guild_var(self, guild_id, key):
        return await _pool.fetchval("select value from guild_vars where guild_id = $1 and key = $2", guild_id, key)

    async def set_guild_var(self, guild_id, key, value):
        await _pool.execute(
            "insert into guild_vars (guild_id, key, value) values ($1, $2, $3) "
            "on conflict (guild_id, key) do update set value = excluded.value",
            guild_id,
            key,
            value,
        )

    async def delete_guild_var(self, guild_id, key):
        await _pool.execute("delete from guild_vars where guild_id = $1 and key = $2", guild_id, key)

    async def search_guild_var(self, key):
        rows = await _pool.fetch("select guild_id, value from guild_vars where key = $1", key)
        return [{"guild_id": r["guild_id"], "value": r["value"]} for r in rows]

    # --- member vars ---
    async def get_member_var(self, guild_id, member_id, key):
        return await _pool.fetchval(
            "select value from member_vars where guild_id = $1 and member_id = $2 and key = $3",
            guild_id,
            member_id,
            key,
        )

    async def set_member_var(self, guild_id, member_id, key, value):
        await _pool.execute(
            "insert into member_vars (guild_id, member_id, key, value) values ($1, $2, $3, $4) "
            "on conflict (guild_id, member_id, key) do update set value = excluded.value",
            guild_id,
            member_id,
            key,
            value,
        )

    async def delete_member_var(self, guild_id, member_id, key):
        await _pool.execute(
            "delete from member_vars where guild_id = $1 and member_id = $2 and key = $3", guild_id, member_id, key
        )

    async def search_member_var(self, key):
        rows = await _pool.fetch("select guild_id, member_id, value from member_vars where key = $1", key)
        return [{"guild_id": r["guild_id"], "member_id": r["member_id"], "value": r["value"]} for r in rows]

    # --- user facts ---
    async def set_user_fact(self, guild_id, user_id, key, value):
        await _pool.execute(
            "insert into user_facts (guild_id, user_id, key, value) values ($1, $2, $3, $4) "
            "on conflict (guild_id, user_id, key) do update set value = excluded.value",
            guild_id,
            user_id,
            key,
            value,
        )

    async def delete_user_fact(self, guild_id, user_id, key):
        await _pool.execute(
            "delete from user_facts where guild_id = $1 and user_id = $2 and key = $3", guild_id, user_id, key
        )

    async def get_user_facts(self, guild_id, user_id):
        rows = await _pool.fetch("select key, value from user_facts where guild_id = $1 and user_id = $2", guild_id, user_id)
        return [{"key": r["key"], "value": r["value"]} for r in rows]

    # --- chat memory ---
    async def add_chat_memory(self, guild_id, channel_id, user_id, role, content, ts):
        await _pool.execute(
            "insert into chat_memory (guild_id, channel_id, user_id, role, content, created_at) "
            "values ($1, $2, $3, $4, $5, $6)",
            guild_id,
            channel_id,
            user_id,
            role,
            content,
            datetime.fromtimestamp(ts / 1000, tz=timezone.utc),
        )

    async def get_chat_memory(self, guild_id, channel_id, user_id, limit):
        rows = await _pool.fetch(
            "select role, content, created_at from chat_memory "
            "where guild_id = $1 and channel_id = $2 and user_id = $3 "
            "order by created_at desc limit $4",
            guild_id,
            channel_id,
            user_id,
            limit,
        )
        return [
            {"role": r["role"], "content": r["content"], "ts": int(r["created_at"].timestamp() * 1000)} for r in rows
        ]

    # --- erasure ---
    async def delete_user_data(self, user_id):
        return {
            "chat_memory": _deleted(await _pool.execute("delete from chat_memory where user_id = $1", user_id)),
            "user_facts": _deleted(await _pool.execute("delete from user_facts where user_id = $1", user_id)),
            "member_vars": _deleted(await _pool.execute("delete from member_vars where member_id = $1", user_id)),
        }


neon = NeonBackend()
