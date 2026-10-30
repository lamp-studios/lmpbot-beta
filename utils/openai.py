# OpenAI chat helper, over the Chat Completions HTTP API. No client library:
# the API is two endpoints and this keeps the dependency list short.
#
# OPENAI_BASE_URL can point at any OpenAI-compatible endpoint (Azure gateways,
# OpenRouter, a local proxy), which is why nothing here assumes a fixed model
# list; whatever the account can see is what /setchatbotai offers.

import asyncio
import json

import aiohttp

from config import config
from utils.memory import to_chat_messages

CHAT_TIMEOUT_S = 120
SHORT_TIMEOUT_S = 15


def base_url() -> str:
    return (config.openai_base_url or "https://api.openai.com/v1").rstrip("/")


def has_key() -> bool:
    return bool(config.openai_api_key)


def _error_from(status: int, text: str) -> str:
    """Pull the useful message out of OpenAI's error envelope."""
    try:
        parsed = json.loads(text)
        message = (parsed.get("error") or {}).get("message") if isinstance(parsed.get("error"), dict) else None
        message = message or parsed.get("message")
        if message:
            return f"{message} (HTTP {status})"
    except (ValueError, AttributeError):
        pass  # not JSON, fall through to the raw body
    return f"HTTP {status}" + (f": {text[:300]}" if text else "")


async def _request(path: str, *, method: str = "GET", body=None, timeout: int = SHORT_TIMEOUT_S):
    """Make a request and return the parsed JSON body; raises with a readable message."""
    if not has_key():
        raise RuntimeError("OPENAI_API_KEY isn't set on the bot")

    headers = {"Authorization": f"Bearer {config.openai_api_key}"}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.request(method, f"{base_url()}{path}", headers=headers, json=body) as res:
                text = await res.text()
                if res.status >= 400:
                    raise RuntimeError(f"OpenAI returned {_error_from(res.status, text)}")
                return json.loads(text)
    except asyncio.TimeoutError:
        raise RuntimeError(f"OpenAI timed out after {timeout}s") from None
    except aiohttp.ClientError as err:
        raise RuntimeError(f"can't reach OpenAI at {base_url()} ({err})") from None


async def list_models() -> list[str]:
    """Model ids the API key can see."""
    data = await _request("/models")
    return sorted(m["id"] for m in (data or {}).get("data") or [] if m.get("id"))


async def has_model(name: str):
    """
    Whether the key can use this model. Returns "unknown" when the endpoint
    doesn't support listing (some OpenAI-compatible proxies don't), so callers
    can let the name through instead of blocking on a check that can't be made.
    """
    try:
        models = await list_models()
    except Exception:
        return "unknown"
    if not models:
        return "unknown"
    return str(name).strip() in models


async def chat(prompt: str, history: list[dict] | None = None, model: str | None = None, images=None):
    """
    Send a prompt to an OpenAI model with optional prior history and images.
    Images ride along on the newest user message as data URIs, which is what the
    Chat Completions API takes; the model has to be a vision one to use them.
    Returns the reply text, or None.
    """
    if not has_key():
        print("[openai] OPENAI_API_KEY not set")
        return None
    if not model:
        print("[openai] no model set")
        return None

    messages = to_chat_messages(history, prompt)
    if images:
        last = messages[-1]
        last["content"] = [
            {"type": "text", "text": last["content"]},
            *(
                {"type": "image_url", "image_url": {"url": f"data:{img['mime_type']};base64,{img['data']}"}}
                for img in images
            ),
        ]

    data = await _request(
        "/chat/completions",
        method="POST",
        body={"model": model, "messages": messages},
        timeout=CHAT_TIMEOUT_S,
    )

    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        text = None
    if not text:
        print("[openai] empty response:", json.dumps(data)[:300])
        return None
    return text
