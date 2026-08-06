// OpenAI chat helper, over the Chat Completions HTTP API. No client library:
// the API is two endpoints and this keeps the dependency list short.
//
// OPENAI_BASE_URL can point at any OpenAI-compatible endpoint (Azure gateways,
// OpenRouter, a local proxy), which is why nothing here assumes a fixed model
// list; whatever the account can see is what /setchatbotai offers.

import { config } from "../config.js";
import { toChatMessages } from "./memory.js";

const CHAT_TIMEOUT_MS = 120_000;
const SHORT_TIMEOUT_MS = 15_000;

function baseUrl() {
  return (config.openaiBaseUrl ?? "https://api.openai.com/v1").replace(/\/+$/, "");
}

export function hasKey() {
  return Boolean(config.openaiApiKey);
}

/** Pull the useful message out of OpenAI's error envelope. */
async function errorFrom(res) {
  const text = await res.text().catch(() => "");
  try {
    const parsed = JSON.parse(text);
    const message = parsed?.error?.message ?? parsed?.message;
    if (message) return `${message} (HTTP ${res.status})`;
  } catch {
    // not JSON, fall through to the raw body
  }
  return `HTTP ${res.status}${text ? `: ${text.slice(0, 300)}` : ""}`;
}

async function request(path, { method = "GET", body, timeout = SHORT_TIMEOUT_MS } = {}) {
  if (!hasKey()) throw new Error("OPENAI_API_KEY isn't set on the bot");

  let res;
  try {
    res = await fetch(`${baseUrl()}${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${config.openaiApiKey}`,
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(timeout),
    });
  } catch (err) {
    if (err?.name === "TimeoutError") throw new Error(`OpenAI timed out after ${timeout / 1000}s`);
    throw new Error(
      `can't reach OpenAI at ${baseUrl()} (${err?.cause?.code ?? err?.message ?? err})`
    );
  }

  if (!res.ok) throw new Error(`OpenAI returned ${await errorFrom(res)}`);
  return res;
}

/** @returns {Promise<string[]>} model ids the API key can see */
export async function listModels() {
  const res = await request("/models");
  const data = await res.json();
  return (data?.data ?? []).map((m) => m.id).filter(Boolean).sort();
}

/**
 * Whether the key can use this model. Returns "unknown" when the endpoint
 * doesn't support listing (some OpenAI-compatible proxies don't), so callers
 * can let the name through instead of blocking on a check that can't be made.
 * @returns {Promise<true|false|"unknown">}
 */
export async function hasModel(name) {
  let models;
  try {
    models = await listModels();
  } catch {
    return "unknown";
  }
  if (models.length === 0) return "unknown";
  return models.includes(String(name).trim());
}

/**
 * Send a prompt to an OpenAI model with optional prior history.
 * @param {string} prompt
 * @param {Array<{role: string, parts: Array<{text: string}>}>} history
 * @param {string} model
 * @returns {Promise<string|null>}
 */
export async function chat(prompt, history = [], model) {
  if (!hasKey()) {
    console.log("[openai] OPENAI_API_KEY not set");
    return null;
  }
  if (!model) {
    console.log("[openai] no model set");
    return null;
  }

  const res = await request("/chat/completions", {
    method: "POST",
    body: { model, messages: toChatMessages(history, prompt) },
    timeout: CHAT_TIMEOUT_MS,
  });

  const data = await res.json();
  const text = data?.choices?.[0]?.message?.content;
  if (!text) {
    console.log("[openai] empty response:", JSON.stringify(data).slice(0, 300));
    return null;
  }
  return text;
}
