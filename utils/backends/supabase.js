import { createClient } from "@supabase/supabase-js";
import { config } from "../../config.js";

let client = null;

// supabase-js returns { data, error } instead of throwing; rethrow so the
// router treats a Supabase failure as a reason to fall through to SQLite.
function unwrap({ data, error }) {
  if (error) throw new Error(`supabase: ${error.message}`);
  return data;
}

export const supabase = {
  name: "supabase",

  async init() {
    if (!config.supabaseUrl || !config.supabaseKey) return false;
    client = createClient(config.supabaseUrl, config.supabaseKey, {
      auth: { persistSession: false },
    });
    return true;
  },

  available() {
    return client !== null;
  },

  // --- guild vars ---
  async getGuildVar(guildId, key) {
    const data = unwrap(
      await client.from("guild_vars").select("value").eq("guild_id", guildId).eq("key", key).maybeSingle()
    );
    return data ? data.value : null;
  },
  async setGuildVar(guildId, key, value) {
    unwrap(
      await client.from("guild_vars").upsert({ guild_id: guildId, key, value }, { onConflict: "guild_id,key" })
    );
  },
  async deleteGuildVar(guildId, key) {
    unwrap(await client.from("guild_vars").delete().eq("guild_id", guildId).eq("key", key));
  },
  async searchGuildVar(key) {
    const data = unwrap(await client.from("guild_vars").select("guild_id,value").eq("key", key));
    return (data ?? []).map((r) => ({ guildId: r.guild_id, value: r.value }));
  },

  // --- member vars ---
  async getMemberVar(guildId, memberId, key) {
    const data = unwrap(
      await client
        .from("member_vars")
        .select("value")
        .eq("guild_id", guildId)
        .eq("member_id", memberId)
        .eq("key", key)
        .maybeSingle()
    );
    return data ? data.value : null;
  },
  async setMemberVar(guildId, memberId, key, value) {
    unwrap(
      await client
        .from("member_vars")
        .upsert({ guild_id: guildId, member_id: memberId, key, value }, { onConflict: "guild_id,member_id,key" })
    );
  },
  async deleteMemberVar(guildId, memberId, key) {
    unwrap(
      await client.from("member_vars").delete().eq("guild_id", guildId).eq("member_id", memberId).eq("key", key)
    );
  },
  async searchMemberVar(key) {
    const data = unwrap(
      await client.from("member_vars").select("guild_id,member_id,value").eq("key", key)
    );
    return (data ?? []).map((r) => ({ guildId: r.guild_id, memberId: r.member_id, value: r.value }));
  },

  // --- user facts ---
  async setUserFact(guildId, userId, key, value) {
    unwrap(
      await client
        .from("user_facts")
        .upsert({ guild_id: guildId, user_id: userId, key, value }, { onConflict: "guild_id,user_id,key" })
    );
  },
  async deleteUserFact(guildId, userId, key) {
    unwrap(
      await client.from("user_facts").delete().eq("guild_id", guildId).eq("user_id", userId).eq("key", key)
    );
  },
  async getUserFacts(guildId, userId) {
    const data = unwrap(
      await client.from("user_facts").select("key,value").eq("guild_id", guildId).eq("user_id", userId)
    );
    return (data ?? []).map((r) => ({ key: r.key, value: r.value }));
  },

  // --- chat memory ---
  async addChatMemory(guildId, channelId, userId, role, content, ts) {
    unwrap(
      await client.from("chat_memory").insert({
        guild_id: guildId,
        channel_id: channelId,
        user_id: userId,
        role,
        content,
        created_at: new Date(ts).toISOString(),
      })
    );
  },
  async getChatMemory(guildId, channelId, userId, limit) {
    const data = unwrap(
      await client
        .from("chat_memory")
        .select("role,content,created_at")
        .eq("guild_id", guildId)
        .eq("channel_id", channelId)
        .eq("user_id", userId)
        .order("created_at", { ascending: false })
        .limit(limit)
    );
    return (data ?? []).map((r) => ({
      role: r.role,
      content: r.content,
      ts: Date.parse(r.created_at),
    }));
  },
};
