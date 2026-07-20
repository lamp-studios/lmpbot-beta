import mongoose from "mongoose";
import { config } from "../../config.js";

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

const GuildVar = model("GuildVar", guildVarSchema);
const MemberVar = model("MemberVar", memberVarSchema);
const UserFact = model("UserFact", userFactSchema);
const ChatMemory = model("ChatMemory", chatMemorySchema);

export const mongo = {
  name: "mongo",

  async init() {
    if (!config.mongoUri) return false;
    await mongoose.connect(config.mongoUri);
    return true;
  },

  available() {
    return Boolean(config.mongoUri) && mongoose.connection.readyState === 1;
  },

  // --- guild vars ---
  async getGuildVar(guildId, key) {
    const row = await GuildVar.findOne({ guildId, key }).lean();
    return row ? row.value : null;
  },
  async setGuildVar(guildId, key, value) {
    await GuildVar.updateOne({ guildId, key }, { $set: { value } }, { upsert: true });
  },
  async deleteGuildVar(guildId, key) {
    await GuildVar.deleteOne({ guildId, key });
  },
  async searchGuildVar(key) {
    const rows = await GuildVar.find({ key }).lean();
    return rows.map((r) => ({ guildId: r.guildId, value: r.value }));
  },

  // --- member vars ---
  async getMemberVar(guildId, memberId, key) {
    const row = await MemberVar.findOne({ guildId, memberId, key }).lean();
    return row ? row.value : null;
  },
  async setMemberVar(guildId, memberId, key, value) {
    await MemberVar.updateOne({ guildId, memberId, key }, { $set: { value } }, { upsert: true });
  },
  async deleteMemberVar(guildId, memberId, key) {
    await MemberVar.deleteOne({ guildId, memberId, key });
  },
  async searchMemberVar(key) {
    const rows = await MemberVar.find({ key }).lean();
    return rows.map((r) => ({ guildId: r.guildId, memberId: r.memberId, value: r.value }));
  },

  // --- user facts ---
  async setUserFact(guildId, userId, key, value) {
    await UserFact.updateOne({ guildId, userId, key }, { $set: { value } }, { upsert: true });
  },
  async deleteUserFact(guildId, userId, key) {
    await UserFact.deleteOne({ guildId, userId, key });
  },
  async getUserFacts(guildId, userId) {
    const rows = await UserFact.find({ guildId, userId }).lean();
    return rows.map((r) => ({ key: r.key, value: r.value }));
  },

  // --- chat memory ---
  async addChatMemory(guildId, channelId, userId, role, content, ts) {
    await ChatMemory.create({
      guildId,
      channelId,
      userId,
      role,
      content,
      createdAt: new Date(ts),
    });
  },
  async getChatMemory(guildId, channelId, userId, limit) {
    const rows = await ChatMemory.find({ guildId, channelId, userId })
      .sort({ createdAt: -1 })
      .limit(limit)
      .lean();
    return rows.map((r) => ({
      role: r.role,
      content: r.content,
      ts: r.createdAt.getTime(),
    }));
  },
};
