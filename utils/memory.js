// Chatbot memory helpers: fact extraction, message scoring, and building a
// compressed Gemini history from stored chat rows.

const IDENTITY_SKIP = new Set([
  "going", "doing", "trying", "eating", "drinking", "playing",
  "watching", "listening", "reading", "writing", "working",
  "learning", "studying", "feeling", "getting", "making",
  "looking", "thinking", "waiting", "coming", "leaving",
  "building",
]);

export function extractFacts(content) {
  const facts = {};

  let m = content.match(/\bmy name is ([A-Za-z][A-Za-z'-]{1,30})/i);
  if (m) facts.name = m[1];

  m = content.match(/\bi am building\s+([^.!?,\n]{3,80})/i);
  if (m) facts.project = m[1].trim();

  m = content.match(/\bi am (?:a |an |the )?(\S[^.!?,\n]{2,49})/i);
  if (m) {
    const val = m[1].trim();
    const first = val ? val.split(/\s+/)[0].toLowerCase() : "";
    if (!IDENTITY_SKIP.has(first) && !first.endsWith("ing")) {
      facts.identity = val;
    }
  }

  m = content.match(/\bi like\s+([^.!?,\n]{3,50})/i);
  if (m) facts.likes = m[1].trim();

  m = content.match(/\bi hate\s+([^.!?,\n]{3,50})/i);
  if (m) facts.hates = m[1].trim();

  return facts;
}

export function scoreMessage(content) {
  const lower = content.toLowerCase();
  let score = 0;

  // length = more likely important
  score += Math.min(Math.floor(content.length / 50), 10);

  const importantKeywords = [
    "remember", "important", "note", "my name is",
    "i am", "i like", "i hate", "always", "never",
    "project", "server", "api", "password", "token",
  ];
  for (const word of importantKeywords) {
    if (lower.includes(word)) score += 5;
  }

  // penalize garbage
  const spammy = ["lol", "lmao", "ok", "k", "hi", "hello", "😂", "💀"];
  if (spammy.includes(lower.trim())) score -= 5;

  return score;
}

export function compressText(text, maxLen) {
  text = text.trim();
  if (text.length <= maxLen) return text;

  // keep start + end (important context usually lives there)
  const half = Math.floor(maxLen / 2);
  return text.slice(0, half) + " ... " + text.slice(text.length - half);
}

/**
 * Build compressed Gemini history from rows.
 * @param {Array<{role: string, content: string}>} rows newest last
 * @returns {Array<{role: string, parts: Array<{text: string}>}>}
 */
export function buildSmartMemory(rows) {
  const scored = rows.map(({ role, content }) => ({
    role,
    content,
    score: scoreMessage(content),
  }));

  // sort by importance (but keep some recency via original index)
  const sorted = scored
    .map((item, idx) => ({ idx, ...item }))
    .sort((a, b) => (a.score !== b.score ? b.score - a.score : b.idx - a.idx));

  const selected = [];
  let totalChars = 0;

  for (const { idx, role, content, score } of sorted) {
    let limit;
    if (score >= 10) limit = 1200;
    else if (score >= 5) limit = 500;
    else if (score >= 0) limit = 200;
    else limit = 80; // trash gets nuked

    const compressed = compressText(content, limit);
    if (totalChars + compressed.length > 7000) continue;

    selected.push({ idx, role, content: compressed });
    totalChars += compressed.length;
  }

  // restore chronological order
  selected.sort((a, b) => a.idx - b.idx);

  return selected.map(({ role, content }) => ({
    role,
    parts: [{ text: content }],
  }));
}

export function formatUptime(seconds) {
  seconds = Math.floor(seconds);
  const weeks = Math.floor(seconds / (7 * 24 * 3600));
  seconds %= 7 * 24 * 3600;
  const days = Math.floor(seconds / (24 * 3600));
  seconds %= 24 * 3600;
  const hours = Math.floor(seconds / 3600);
  seconds %= 3600;
  const minutes = Math.floor(seconds / 60);
  seconds %= 60;

  const parts = [];
  if (weeks) parts.push(`${weeks}w`);
  if (days) parts.push(`${days}d`);
  if (hours) parts.push(`${hours}h`);
  if (minutes) parts.push(`${minutes}m`);
  if (seconds || parts.length === 0) parts.push(`${seconds}s`);
  return parts.join(" ");
}

/**
 * Split text into chunks <= size without breaking words where possible.
 * @returns {string[]}
 */
export function splitMessage(text, size = 2000) {
  if (!text) return ["(empty)"];
  if (text.length <= size) return [text];

  const chunks = [];
  let current = "";
  for (const word of text.split(/(\s+)/)) {
    if (current.length + word.length > size) {
      if (current) chunks.push(current);
      // a single word longer than the limit gets hard-split
      if (word.length > size) {
        for (let i = 0; i < word.length; i += size) {
          chunks.push(word.slice(i, i + size));
        }
        current = "";
      } else {
        current = word;
      }
    } else {
      current += word;
    }
  }
  if (current.trim()) chunks.push(current);
  return chunks.length ? chunks : [text.slice(0, size)];
}
