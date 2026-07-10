import mongoose from "mongoose";

const { Schema, model } = mongoose;

// Discord snowflakes are stored as strings to avoid precision loss.

const guildVarSchema = new Schema({
  guildId: { type: String, required: true },
  key: { type: String, required: true },
  value: String,
});
guildVarSchema.index({ guildId: 1, key: 1 }, { unique: true });

const memberVarSchema = new Schema({
  guildId: { type: String, required: true },
  memberId: { type: String, required: true },
  key: { type: String, required: true },
  value: String,
});
memberVarSchema.index({ guildId: 1, memberId: 1, key: 1 }, { unique: true });

const userFactSchema = new Schema({
  guildId: { type: String, required: true },
  userId: { type: String, required: true },
  key: { type: String, required: true },
  value: String,
});
userFactSchema.index({ guildId: 1, userId: 1, key: 1 }, { unique: true });

const chatMemorySchema = new Schema({
  guildId: String,
  channelId: String,
  userId: String,
  role: String,
  content: String,
  createdAt: { type: Date, default: Date.now },
});

export const GuildVar = model("GuildVar", guildVarSchema);
export const MemberVar = model("MemberVar", memberVarSchema);
export const UserFact = model("UserFact", userFactSchema);
export const ChatMemory = model("ChatMemory", chatMemorySchema);

// -------------------------
// GUILD VARS
// -------------------------

export async function getGuildVar(guildId, key, def = null) {
  const row = await GuildVar.findOne({ guildId: String(guildId), key }).lean();
  return row ? row.value : def;
}

export async function setGuildVar(guildId, key, value) {
  await GuildVar.updateOne(
    { guildId: String(guildId), key },
    { $set: { value: String(value) } },
    { upsert: true }
  );
}

export async function deleteGuildVar(guildId, key) {
  await GuildVar.deleteOne({ guildId: String(guildId), key });
}

export async function searchGuildVar(key) {
  const rows = await GuildVar.find({ key }).lean();
  return rows.map((r) => ({ guildId: r.guildId, value: r.value }));
}

// -------------------------
// MEMBER VARS
// -------------------------

export async function getMemberVar(guildId, memberId, key, def = null) {
  const row = await MemberVar.findOne({
    guildId: String(guildId),
    memberId: String(memberId),
    key,
  }).lean();
  return row ? row.value : def;
}

export async function setMemberVar(guildId, memberId, key, value) {
  await MemberVar.updateOne(
    { guildId: String(guildId), memberId: String(memberId), key },
    { $set: { value: String(value) } },
    { upsert: true }
  );
}

// -------------------------
// USER FACTS
// -------------------------

export async function setUserFact(guildId, userId, key, value) {
  await UserFact.updateOne(
    { guildId: String(guildId), userId: String(userId), key },
    { $set: { value: String(value) } },
    { upsert: true }
  );
}

export async function getUserFacts(guildId, userId) {
  const rows = await UserFact.find({
    guildId: String(guildId),
    userId: String(userId),
  }).lean();
  return Object.fromEntries(rows.map((r) => [r.key, r.value]));
}

// -------------------------
// CHAT MEMORY
// -------------------------

export async function addChatMemory(guildId, channelId, userId, role, content) {
  await ChatMemory.create({
    guildId: String(guildId),
    channelId: String(channelId),
    userId: String(userId),
    role,
    content,
  });
}

export async function getChatMemory(guildId, channelId, userId, limit = 10) {
  const rows = await ChatMemory.find({
    guildId: String(guildId),
    channelId: String(channelId),
    userId: String(userId),
  })
    .sort({ createdAt: -1 })
    .limit(limit)
    .lean();

  // newest last, to match how the memory builder expects history
  return rows.reverse().map((r) => ({ role: r.role, content: r.content }));
}
