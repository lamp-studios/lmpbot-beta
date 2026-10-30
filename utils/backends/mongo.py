from datetime import datetime, timezone

from pymongo import ASCENDING, AsyncMongoClient

from config import config

# Collection and field names match what the earlier mongoose models created
# (model "GuildVar" -> collection "guildvars", and so on), so existing data
# carries over untouched. Discord snowflakes are stored as strings to avoid
# precision loss.

_client: AsyncMongoClient | None = None
_guild_vars = _member_vars = _user_facts = _chat_memory = None


class MongoBackend:
    name = "mongo"

    async def init(self) -> bool:
        global _client, _guild_vars, _member_vars, _user_facts, _chat_memory
        if not config.mongo_uri:
            return False

        client = AsyncMongoClient(
            config.mongo_uri,
            tz_aware=True,
            # fail over to the next backend in seconds rather than the 30s default
            serverSelectionTimeoutMS=5000,
        )
        try:
            await client.admin.command("ping")
            # mongoose fell back to "test" when the URI named no database
            db = client.get_default_database(default="test")
            _guild_vars = db["guildvars"]
            _member_vars = db["membervars"]
            _user_facts = db["userfacts"]
            _chat_memory = db["chatmemories"]

            await _guild_vars.create_index([("guildId", ASCENDING), ("key", ASCENDING)], unique=True)
            await _member_vars.create_index(
                [("guildId", ASCENDING), ("memberId", ASCENDING), ("key", ASCENDING)], unique=True
            )
            await _user_facts.create_index(
                [("guildId", ASCENDING), ("userId", ASCENDING), ("key", ASCENDING)], unique=True
            )
        except Exception:
            await client.close()
            raise

        _client = client
        return True

    def available(self) -> bool:
        # mirrors mongoose's readyState check: skip Mongo while it has no
        # writable server, instead of waiting on every call to time out
        return _client is not None and _client.topology_description.has_writable_server()

    # --- guild vars ---
    async def get_guild_var(self, guild_id, key):
        row = await _guild_vars.find_one({"guildId": guild_id, "key": key})
        return row.get("value") if row else None

    async def set_guild_var(self, guild_id, key, value):
        await _guild_vars.update_one(
            {"guildId": guild_id, "key": key}, {"$set": {"value": value}}, upsert=True
        )

    async def delete_guild_var(self, guild_id, key):
        await _guild_vars.delete_one({"guildId": guild_id, "key": key})

    async def search_guild_var(self, key):
        rows = await _guild_vars.find({"key": key}).to_list()
        return [{"guild_id": r["guildId"], "value": r.get("value")} for r in rows]

    # --- member vars ---
    async def get_member_var(self, guild_id, member_id, key):
        row = await _member_vars.find_one({"guildId": guild_id, "memberId": member_id, "key": key})
        return row.get("value") if row else None

    async def set_member_var(self, guild_id, member_id, key, value):
        await _member_vars.update_one(
            {"guildId": guild_id, "memberId": member_id, "key": key},
            {"$set": {"value": value}},
            upsert=True,
        )

    async def delete_member_var(self, guild_id, member_id, key):
        await _member_vars.delete_one({"guildId": guild_id, "memberId": member_id, "key": key})

    async def search_member_var(self, key):
        rows = await _member_vars.find({"key": key}).to_list()
        return [
            {"guild_id": r["guildId"], "member_id": r["memberId"], "value": r.get("value")}
            for r in rows
        ]

    # --- user facts ---
    async def set_user_fact(self, guild_id, user_id, key, value):
        await _user_facts.update_one(
            {"guildId": guild_id, "userId": user_id, "key": key},
            {"$set": {"value": value}},
            upsert=True,
        )

    async def delete_user_fact(self, guild_id, user_id, key):
        await _user_facts.delete_one({"guildId": guild_id, "userId": user_id, "key": key})

    async def get_user_facts(self, guild_id, user_id):
        rows = await _user_facts.find({"guildId": guild_id, "userId": user_id}).to_list()
        return [{"key": r["key"], "value": r.get("value")} for r in rows]

    # --- chat memory ---
    async def add_chat_memory(self, guild_id, channel_id, user_id, role, content, ts):
        await _chat_memory.insert_one(
            {
                "guildId": guild_id,
                "channelId": channel_id,
                "userId": user_id,
                "role": role,
                "content": content,
                "createdAt": datetime.fromtimestamp(ts / 1000, tz=timezone.utc),
            }
        )

    async def get_chat_memory(self, guild_id, channel_id, user_id, limit):
        rows = (
            await _chat_memory.find({"guildId": guild_id, "channelId": channel_id, "userId": user_id})
            .sort("createdAt", -1)
            .limit(limit)
            .to_list()
        )
        return [
            {
                "role": r.get("role"),
                "content": r.get("content"),
                "ts": int(r["createdAt"].timestamp() * 1000),
            }
            for r in rows
        ]

    # --- erasure ---
    async def delete_user_data(self, user_id):
        chat = await _chat_memory.delete_many({"userId": user_id})
        facts = await _user_facts.delete_many({"userId": user_id})
        members = await _member_vars.delete_many({"memberId": user_id})
        return {
            "chat_memory": chat.deleted_count,
            "user_facts": facts.deleted_count,
            "member_vars": members.deleted_count,
        }


mongo = MongoBackend()
