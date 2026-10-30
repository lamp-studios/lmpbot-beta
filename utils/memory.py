# Chatbot memory helpers: fact extraction, message scoring, and building a
# compressed chat history from stored rows.

import math
import re


def extract_facts(content: str) -> dict[str, str]:
    facts = {}

    m = re.search(r"\bmy name is ([A-Za-z][A-Za-z'-]{1,30})", content, re.I)
    if m:
        facts["name"] = m.group(1)

    m = re.search(r"\bi am building\s+([^.!?,\n]{3,80})", content, re.I)
    if m:
        facts["project"] = m.group(1).strip()

    m = re.search(r"\bi am (?:a |an |the )?(\S[^.!?,\n]{2,49})", content, re.I)
    if m:
        facts["identity"] = m.group(1).strip()

    m = re.search(r"\bi like\s+([^.!?,\n]{3,50})", content, re.I)
    if m:
        facts["likes"] = m.group(1).strip()

    m = re.search(r"\bi hate\s+([^.!?,\n]{3,50})", content, re.I)
    if m:
        facts["hates"] = m.group(1).strip()

    return facts


IMPORTANT_KEYWORDS = [
    "remember", "important", "note", "my name is",
    "i am", "i like", "i hate", "always", "never",
    "project", "server", "api", "password", "token",
]


def score_message(content: str) -> int:
    lower = content.lower()
    score = 0

    # length = more likely important
    score += min(len(content) // 50, 10)

    for word in IMPORTANT_KEYWORDS:
        if word in lower:
            score += 5

    # penalize garbage
    spammy = ["lmaoooo"]
    if lower.strip() in spammy:
        score -= 5

    return score


def compress_text(text: str, max_len: int) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text

    # keep start + end (important context usually lives there)
    half = max_len // 2
    return text[:half] + " ... " + text[len(text) - half:]


def build_smart_memory(rows: list[dict]) -> str:
    """
    Build a compressed transcript from rows (newest last).
    Returns a formatted transcript string, oldest to newest, with a blank
    line between each message so the model can tell them apart.
    """
    scored = [
        {"idx": idx, "role": r["role"], "content": r["content"] or "", "score": score_message(r["content"] or "")}
        for idx, r in enumerate(rows)
    ]

    # sort by importance (but keep some recency via original index)
    ordered = sorted(scored, key=lambda item: (-item["score"], -item["idx"]))

    selected = []
    total_chars = 0

    for item in ordered:
        # gentle compression - keep most messages mostly intact
        score = item["score"]
        if score >= 10:
            limit = 2000
        elif score >= 5:
            limit = 1400
        elif score >= 0:
            limit = 800
        else:
            limit = 400

        compressed = compress_text(item["content"], limit)
        if total_chars + len(compressed) > 20000:
            continue

        selected.append({"idx": item["idx"], "role": item["role"], "content": compressed})
        total_chars += len(compressed)

    # restore chronological order
    selected.sort(key=lambda item: item["idx"])

    # one message per block, blank line between each, labelled by speaker
    return "\n\n".join(
        f"{'User' if item['role'] == 'user' else 'Bot'}: {item['content']}" for item in selected
    )


def to_chat_messages(history: list[dict], prompt: str) -> list[dict]:
    """
    History is passed around in the Gemini shape ({"role", "parts": [{"text"}]}),
    so every provider takes the same arguments. This converts it to the
    role/content messages that OpenAI-style APIs (and Ollama) expect, with the
    new prompt appended.
    """
    messages = []
    for entry in history or []:
        role = entry.get("role")
        messages.append(
            {
                "role": "assistant" if role == "model" else "system" if role == "system" else "user",
                "content": "\n".join((p or {}).get("text", "") or "" for p in entry.get("parts") or []),
            }
        )
    messages.append({"role": "user", "content": prompt})
    return messages


def format_uptime(seconds: float) -> str:
    seconds = math.floor(seconds)
    weeks, seconds = divmod(seconds, 7 * 24 * 3600)
    days, seconds = divmod(seconds, 24 * 3600)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []
    if weeks:
        parts.append(f"{weeks}w")
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)


def split_message(text: str, size: int = 2000) -> list[str]:
    """Split text into chunks <= size without breaking words where possible."""
    if not text:
        return ["(empty)"]
    if len(text) <= size:
        return [text]

    chunks = []
    current = ""
    for word in re.split(r"(\s+)", text):
        if len(current) + len(word) > size:
            if current:
                chunks.append(current)
            # a single word longer than the limit gets hard-split
            if len(word) > size:
                for i in range(0, len(word), size):
                    chunks.append(word[i:i + size])
                current = ""
            else:
                current = word
        else:
            current += word
    if current.strip():
        chunks.append(current)
    return chunks or [text[:size]]
