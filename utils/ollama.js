// Ollama chat helper. Talks to an Ollama server over its HTTP API, so the bot
// doesn't need the `ollama` binary on the same host; point OLLAMA_HOST at
// wherever it runs.

import { config } from "../config.js";
import { toChatMessages } from "./memory.js";

const CHAT_TIMEOUT_MS = 180_000;
const SHORT_TIMEOUT_MS = 10_000;

function host() {
  return (config.ollamaHost ?? "http://127.0.0.1:11434").replace(/\/+$/, "");
}

/** Ollama defaults an untagged name to `:latest`, so compare the same way. */
function normalizeModel(name) {
  const trimmed = String(name ?? "").trim();
  return trimmed.includes(":") ? trimmed : `${trimmed}:latest`;
}

function unreachable(err) {
  return new Error(
    `can't reach the Ollama server at ${host()} (${err?.cause?.code ?? err?.message ?? err}). ` +
      "Make sure `ollama serve` is running, or set OLLAMA_HOST."
  );
}

async function request(path, { method = "GET", body, timeout = SHORT_TIMEOUT_MS } = {}) {
  let res;
  try {
    res = await fetch(`${host()}${path}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(timeout),
    });
  } catch (err) {
    if (err?.name === "TimeoutError") throw new Error(`Ollama timed out after ${timeout / 1000}s`);
    throw unreachable(err);
  }
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Ollama returned HTTP ${res.status}${text ? `: ${text.slice(0, 300)}` : ""}`);
  }
  return res;
}

/** True if the server answers, false if it's down or not an Ollama server. */
export async function reachable() {
  try {
    await request("/api/tags");
    return true;
  } catch {
    return false;
  }
}

/** @returns {Promise<string[]>} installed model names, e.g. ["llama3:latest"] */
export async function listModels() {
  const res = await request("/api/tags");
  const data = await res.json();
  return (data?.models ?? []).map((m) => m.name ?? m.model).filter(Boolean);
}

export async function hasModel(name) {
  const wanted = normalizeModel(name);
  return (await listModels()).some((m) => normalizeModel(m) === wanted);
}

/**
 * Pull a model, streaming progress back as it downloads. Resolves once the
 * server reports success; throws with the server's own message otherwise.
 * @param {string} name model to pull, e.g. "llama3" or "qwen2.5:7b"
 * @param {(evt: {status?: string, total?: number, completed?: number}) => void} [onProgress]
 */
export async function pullModel(name, onProgress) {
  let res;
  try {
    res = await fetch(`${host()}/api/pull`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: String(name).trim(), stream: true }),
    });
  } catch (err) {
    throw unreachable(err);
  }
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`pull failed (HTTP ${res.status})${text ? `: ${text.slice(0, 300)}` : ""}`);
  }

  // NDJSON: one JSON object per line, and the last line may arrive unterminated
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let last = null;

  const handle = (line) => {
    if (!line.trim()) return;
    let evt;
    try {
      evt = JSON.parse(line);
    } catch {
      return; // partial or non-JSON noise, nothing useful to report
    }
    if (evt.error) throw new Error(evt.error);
    last = evt;
    onProgress?.(evt);
  };

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) handle(line);
    }
    handle(buffer);
  } catch (err) {
    // don't leave the download running behind a failed pull
    await reader.cancel().catch(() => {});
    throw err;
  }

  if (last?.status && last.status !== "success") {
    throw new Error(`pull ended on "${last.status}" instead of success`);
  }
  return last;
}

/**
 * Send a prompt to an Ollama model with optional prior history.
 * @param {string} prompt
 * @param {Array<{role: string, parts: Array<{text: string}>}>} history
 * @param {string} model
 * @returns {Promise<string|null>}
 */
export async function chat(prompt, history = [], model) {
  if (!model) {
    console.log("[ollama] no model set");
    return null;
  }

  const res = await request("/api/chat", {
    method: "POST",
    body: { model, messages: toChatMessages(history, prompt), stream: false },
    timeout: CHAT_TIMEOUT_MS,
  });

  const data = await res.json();
  const text = data?.message?.content;
  if (!text) {
    console.log("[ollama] empty response:", JSON.stringify(data).slice(0, 300));
    return null;
  }
  return text;
}
