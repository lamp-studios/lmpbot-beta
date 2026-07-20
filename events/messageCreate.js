import os from "node:os";
import { Events, EmbedBuilder } from "discord.js";
import * as Discord from "discord.js";
import { config } from "../config.js";
import {
  getGuildVar,
  getMemberVar,
  setMemberVar,
  searchGuildVar,
  setUserFact,
  getUserFacts,
  addChatMemory,
  getChatMemory,
} from "../utils/db.js";
import * as gemini from "../utils/gemini.js";
import {
  extractFacts,
  buildSmartMemory,
  formatUptime,
  splitMessage,
} from "../utils/memory.js";

const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

function isOwner(message) {
  return message.client.ownerIds.has(message.author.id);
}

export default {
  name: Events.MessageCreate,

  async execute(message, client) {
    if (message.author.bot || !message.guild) return;

    const guildId = message.guild.id;

    // dont_talk channel: auto-ban anyone who messages there
    const dontTalk = await getGuildVar(guildId, "dont_talk_channel");
    if (dontTalk && message.channel.id === dontTalk) {
      try {
        await message.delete();
        await message.author.send("Bot detected!!!").catch(() => {});
        await message.guild.members.ban(message.author, {
          reason: "spambot detected",
          deleteMessageSeconds: 120,
        });
        await message.guild.members.unban(
          message.author,
          "spambot detection unban system"
        );
      } catch (err) {
        if (err?.code !== 50013) console.error("dont_talk ban failed:", err);
      }
      return;
    }

    // chatbot channel
    const chatbotCh = await getGuildVar(guildId, "chatbot_channel");
    if (chatbotCh && message.channel.id === chatbotCh) {
      const loading = await message.channel.send(
        "Loading... <a:CircleLoader:1492857500637335685>"
      );

      // SAVE USER MESSAGE + FETCH HISTORY
      await addChatMemory(
        guildId,
        message.channel.id,
        message.author.id,
        "user",
        message.content
      );

      const rows = await getChatMemory(
        guildId,
        message.channel.id,
        message.author.id,
        50
      );
      const transcript = buildSmartMemory(rows);

      const history = [];
      if (transcript) {
        history.push({
          role: "user",
          parts: [
            {
              text:
                "The following is our chat history so far (oldest to newest), for context:\n\n" +
                transcript,
            },
          ],
        });
      }

      const facts = extractFacts(message.content);
      for (const [k, v] of Object.entries(facts)) {
        if (v.length > 2) {
          await setUserFact(guildId, message.author.id, k, v);
        }
      }

      const userFacts = await getUserFacts(guildId, message.author.id);
      if (Object.keys(userFacts).length) {
        const factText = Object.entries(userFacts)
          .map(([k, v]) => `${k}: ${v}`)
          .join("\n");
        history.unshift({
          role: "user",
          parts: [{ text: `User facts:\n${factText}` }],
        });
      }

      // CALL GEMINI
      let reply;
      try {
        reply = await gemini.chat(message.content, history);
      } catch (err) {
        await loading.edit(`Gemini failed. ${err}`);
        return;
      }

      if (reply === null) {
        await loading.edit("Gemini failed.");
        return;
      }

      // SAVE BOT RESPONSE
      await addChatMemory(
        guildId,
        message.channel.id,
        message.author.id,
        "model",
        reply
      );

      // SEND RESPONSE
      const chunks = splitMessage(reply, 2000);
      await loading.edit(chunks[0]);
      for (const chunk of chunks.slice(1)) {
        await message.channel.send(chunk);
      }

      return;
    }

    // prefix commands
    if (!message.content.startsWith(config.prefix)) return;

    const parts = message.content.slice(config.prefix.length).split(/\s+(.+)/s);
    const cmd = (parts[0] || "").toLowerCase();
    const args = parts[1] || "";

    if (cmd === "ping") {
      await message.channel.send(`Pong! ${Math.round(client.ws.ping)}ms`);
    } else if (cmd === "info") {
      const uptime = formatUptime((Date.now() - client.startTime) / 1000);
      const embed = new EmbedBuilder()
        .setTitle("Bot Information")
        .setColor("Random")
        .addFields(
          { name: "Ping", value: `${Math.round(client.ws.ping)}ms` },
          { name: "Uptime", value: uptime },
          { name: "OS", value: os.type() }
        );
      await message.channel.send({ embeds: [embed] });
    } else if (cmd === "verify") {
      const enabled = await getGuildVar(guildId, "verification_enabled");
      if (!enabled) {
        const msg = await message.channel.send("Verification is not enabled on this server.");
        setTimeout(() => msg.delete().catch(() => {}), 2000);
        return;
      }
      const verified = await getMemberVar(guildId, message.author.id, "is_verified");
      if (verified === "true") {
        await message.channel.send("You are already verified!");
        return;
      }
      await setMemberVar(guildId, message.author.id, "is_verified", "true");

      const roleId = await getGuildVar(guildId, "verification_role");
      const role = roleId
        ? message.guild.roles.cache.get(roleId)
        : message.guild.roles.cache.find((r) => r.name === "verified");
      if (role) await message.member.roles.add(role);

      await message.channel.send("Verified successfully!");
    } else if (cmd === "up") {
      if (!isOwner(message)) return;
      const { registerCommands } = await import("../utils/deploy.js");
      await registerCommands(client);
      await message.react("\u{1F44D}\u{1F3FB}");
    } else if (cmd === "exe") {
      if (!isOwner(message)) return;
      if (!args) return;
      try {
        const fn = new AsyncFunction("bot", "client", "message", "discord", args);
        const result = await fn(client, client, message, Discord);
        if (result !== undefined && result !== null) {
          await message.channel.send(String(result).slice(0, 2000));
        }
      } catch (err) {
        await message.channel.send("```\n" + String(err?.stack ?? err).slice(0, 1900) + "\n```");
      }
    } else if (cmd === "send_new") {
      if (!isOwner(message)) return;
      const rows = await searchGuildVar("news_channel");
      for (const { value: channelId } of rows) {
        const ch =
          client.channels.cache.get(channelId) ??
          (await client.channels.fetch(channelId).catch(() => null));
        if (ch) await ch.send(args.slice(0, 2000));
      }
    }
  },
};
