// Chatbot provider router.
//
// Which AI answers is a bot-owner setting with two scopes: a global default
// used by every server, and a per-server override on top of it. Lookups go
// server -> global -> Gemini, so a server that was never touched keeps the
// original behaviour, and clearing an override drops that server back to the
// global default rather than to nothing.
//
// The global row is stored as a guild var under the id "global". Guild ids are
// numeric snowflakes, so it can't collide with a real server.

import * as gemini from "./gemini.js";
import * as openai from "./openai.js";
import * as ollama from "./ollama.js";
import { getGuildVar, setGuildVar, deleteGuildVar } from "./db.js";

export const PROVIDER_KEY = "chatbot_ai";
export const MODEL_KEY = "chatbot_ai_model";
export const GLOBAL_ID = "global";

export const PROVIDERS = ["gemini", "openai", "ollama"];
export const DEFAULT_PROVIDER = "gemini";

const NAMES = { gemini: "Gemini", openai: "OpenAI", ollama: "Ollama" };

/** Only Gemini has a usable default; the others are meaningless without a model. */
function defaultModel(provider) {
  return provider === "gemini" ? gemini.DEFAULT_MODEL : null;
}

async function readScope(id) {
  const provider = await getGuildVar(id, PROVIDER_KEY);
  if (!provider || !PROVIDERS.includes(provider)) return null;
  const model = await getGuildVar(id, MODEL_KEY);
  return { provider, model: model || defaultModel(provider) };
}

/**
 * The AI in effect for a guild, and where the setting came from:
 * "server" (this guild's override), "global" (the owner's default for every
 * guild) or "default" (nothing configured anywhere).
 * @returns {Promise<{provider: string, model: string|null, scope: string}>}
 */
export async function getSettings(guildId) {
  const server = guildId ? await readScope(guildId) : null;
  if (server) return { ...server, scope: "server" };

  const global = await readScope(GLOBAL_ID);
  if (global) return { ...global, scope: "global" };

  return { provider: DEFAULT_PROVIDER, model: defaultModel(DEFAULT_PROVIDER), scope: "default" };
}

/** The global default on its own, ignoring any server override. */
export async function getGlobalSettings() {
  const global = await readScope(GLOBAL_ID);
  if (global) return { ...global, scope: "global" };
  return { provider: DEFAULT_PROVIDER, model: defaultModel(DEFAULT_PROVIDER), scope: "default" };
}

/**
 * Write a setting. `id` is a guild id for a server override, or GLOBAL_ID for
 * the default every server falls back to.
 */
export async function setSettings(id, provider, model) {
  await setGuildVar(id, PROVIDER_KEY, provider);
  if (model) await setGuildVar(id, MODEL_KEY, model);
  else await deleteGuildVar(id, MODEL_KEY);
}

/** Drop a server's override so it follows the global default again. */
export async function clearSettings(id) {
  await deleteGuildVar(id, PROVIDER_KEY);
  await deleteGuildVar(id, MODEL_KEY);
}

/** Human-readable name for replies and error messages. */
export function label(provider, model) {
  const name = NAMES[provider] ?? provider;
  return model ? `${name} (${model})` : name;
}

/**
 * Send a prompt to whichever provider the guild is on.
 * `text` is null when the provider failed softly (see the bot logs); anything
 * worth telling the user about is thrown with a message they can act on.
 * @param {Array<{mimeType: string, data: string}>} [images] base64 images to
 *   attach to the prompt; whether they're understood is down to the model.
 * @returns {Promise<{text: string|null, provider: string, model: string|null, scope: string, label: string}>}
 */
export async function chat(guildId, prompt, history = [], images = []) {
  const { provider, model, scope } = await getSettings(guildId);

  let text;
  if (provider === "ollama") text = await ollama.chat(prompt, history, model, images);
  else if (provider === "openai") text = await openai.chat(prompt, history, model, images);
  else text = await gemini.chat(prompt, history, model, images);

  return { text, provider, model, scope, label: label(provider, model) };
}
