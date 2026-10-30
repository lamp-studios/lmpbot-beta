from postgrest import CountMethod
from supabase import AsyncClient, AsyncClientOptions, acreate_client

from config import config
from utils.backends.timestamps import parse_iso, to_iso

# supabase-py raises APIError on a failed request, so a Supabase failure
# already reaches the router as an exception and falls through to SQLite.

_client: AsyncClient | None = None


class SupabaseBackend:
    name = "supabase"

    async def init(self) -> bool:
        global _client
        if not config.supabase_url or not config.supabase_key:
            return False
        _client = await acreate_client(
            config.supabase_url,
            config.supabase_key,
            options=AsyncClientOptions(persist_session=False, auto_refresh_token=False),
        )
        return True

    def available(self) -> bool:
        return _client is not None

    # --- guild vars ---
    async def get_guild_var(self, guild_id, key):
        res = (
            await _client.table("guild_vars")
            .select("value")
            .eq("guild_id", guild_id)
            .eq("key", key)
            .maybe_single()
            .execute()
        )
        return res.data["value"] if res and res.data else None

    async def set_guild_var(self, guild_id, key, value):
        await (
            _client.table("guild_vars")
            .upsert({"guild_id": guild_id, "key": key, "value": value}, on_conflict="guild_id,key")
            .execute()
        )

    async def delete_guild_var(self, guild_id, key):
        await _client.table("guild_vars").delete().eq("guild_id", guild_id).eq("key", key).execute()

    async def search_guild_var(self, key):
        res = await _client.table("guild_vars").select("guild_id,value").eq("key", key).execute()
        return [{"guild_id": r["guild_id"], "value": r["value"]} for r in res.data or []]

    # --- member vars ---
    async def get_member_var(self, guild_id, member_id, key):
        res = (
            await _client.table("member_vars")
            .select("value")
            .eq("guild_id", guild_id)
            .eq("member_id", member_id)
            .eq("key", key)
            .maybe_single()
            .execute()
        )
        return res.data["value"] if res and res.data else None

    async def set_member_var(self, guild_id, member_id, key, value):
        await (
            _client.table("member_vars")
            .upsert(
                {"guild_id": guild_id, "member_id": member_id, "key": key, "value": value},
                on_conflict="guild_id,member_id,key",
            )
            .execute()
        )

    async def delete_member_var(self, guild_id, member_id, key):
        await (
            _client.table("member_vars")
            .delete()
            .eq("guild_id", guild_id)
            .eq("member_id", member_id)
            .eq("key", key)
            .execute()
        )

    async def search_member_var(self, key):
        res = (
            await _client.table("member_vars")
            .select("guild_id,member_id,value")
            .eq("key", key)
            .execute()
        )
        return [
            {"guild_id": r["guild_id"], "member_id": r["member_id"], "value": r["value"]}
            for r in res.data or []
        ]

    # --- user facts ---
    async def set_user_fact(self, guild_id, user_id, key, value):
        await (
            _client.table("user_facts")
            .upsert(
                {"guild_id": guild_id, "user_id": user_id, "key": key, "value": value},
                on_conflict="guild_id,user_id,key",
            )
            .execute()
        )

    async def delete_user_fact(self, guild_id, user_id, key):
        await (
            _client.table("user_facts")
            .delete()
            .eq("guild_id", guild_id)
            .eq("user_id", user_id)
            .eq("key", key)
            .execute()
        )

    async def get_user_facts(self, guild_id, user_id):
        res = (
            await _client.table("user_facts")
            .select("key,value")
            .eq("guild_id", guild_id)
            .eq("user_id", user_id)
            .execute()
        )
        return [{"key": r["key"], "value": r["value"]} for r in res.data or []]

    # --- chat memory ---
    async def add_chat_memory(self, guild_id, channel_id, user_id, role, content, ts):
        await (
            _client.table("chat_memory")
            .insert(
                {
                    "guild_id": guild_id,
                    "channel_id": channel_id,
                    "user_id": user_id,
                    "role": role,
                    "content": content,
                    "created_at": to_iso(ts),
                }
            )
            .execute()
        )

    async def get_chat_memory(self, guild_id, channel_id, user_id, limit):
        res = (
            await _client.table("chat_memory")
            .select("role,content,created_at")
            .eq("guild_id", guild_id)
            .eq("channel_id", channel_id)
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [
            {"role": r["role"], "content": r["content"], "ts": parse_iso(r["created_at"])}
            for r in res.data or []
        ]

    # --- erasure ---
    async def delete_user_data(self, user_id):
        # count=exact makes PostgREST report how many rows the delete hit
        async def wipe(table, column):
            res = await _client.table(table).delete(count=CountMethod.exact).eq(column, user_id).execute()
            return res.count

        return {
            "chat_memory": await wipe("chat_memory", "user_id"),
            "user_facts": await wipe("user_facts", "user_id"),
            "member_vars": await wipe("member_vars", "member_id"),
        }


supabase = SupabaseBackend()
