# Ollama chat helper. Talks to an Ollama server over its HTTP API, so the bot
# doesn't need the `ollama` binary on the same host; point OLLAMA_HOST at
# wherever it runs.

import asyncio
import json

import aiohttp

from config import config
from utils.memory import to_chat_messages

CHAT_TIMEOUT_S = 180
SHORT_TIMEOUT_S = 10


def host() -> str:
    return (config.ollama_host or "http://127.0.0.1:11434").rstrip("/")


def _normalize_model(name) -> str:
    """Ollama defaults an untagged name to `:latest`, so compare the same way."""
    trimmed = str(name or "").strip()
    return trimmed if ":" in trimmed else f"{trimmed}:latest"


def _unreachable(err) -> RuntimeError:
    return RuntimeError(
        f"can't reach the Ollama server at {host()} ({err}). "
        "Make sure `ollama serve` is running, or set OLLAMA_HOST."
    )


async def _request(path: str, *, method: str = "GET", body=None, timeout: int = SHORT_TIMEOUT_S):
    """Make a request and return the parsed JSON body; raises with a readable message."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.request(method, f"{host()}{path}", json=body) as res:
                text = await res.text()
                if res.status >= 400:
                    raise RuntimeError(f"Ollama returned HTTP {res.status}" + (f": {text[:300]}" if text else ""))
                return json.loads(text)
    except asyncio.TimeoutError:
        raise RuntimeError(f"Ollama timed out after {timeout}s") from None
    except aiohttp.ClientError as err:
        raise _unreachable(err) from None


async def reachable() -> bool:
    """True if the server answers, False if it's down or not an Ollama server."""
    try:
        await _request("/api/tags")
        return True
    except Exception:
        return False


async def list_models() -> list[str]:
    """Installed model names, e.g. ["llama3:latest"]."""
    data = await _request("/api/tags")
    return [name for m in (data or {}).get("models") or [] if (name := m.get("name") or m.get("model"))]


async def has_model(name: str) -> bool:
    wanted = _normalize_model(name)
    return any(_normalize_model(m) == wanted for m in await list_models())


async def pull_model(name: str, on_progress=None):
    """
    Pull a model, streaming progress back as it downloads. Resolves once the
    server reports success; raises with the server's own message otherwise.
    `on_progress` is called with each status dict ({"status", "total", "completed"}).
    """
    last = None

    def handle(line: bytes):
        nonlocal last
        if not line.strip():
            return
        try:
            evt = json.loads(line)
        except ValueError:
            return  # partial or non-JSON noise, nothing useful to report
        if not isinstance(evt, dict):
            return
        if evt.get("error"):
            raise RuntimeError(evt["error"])
        last = evt
        if on_progress:
            on_progress(evt)

    # no overall timeout: a big model can take far longer than any sane limit
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=SHORT_TIMEOUT_S)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{host()}/api/pull", json={"model": str(name).strip(), "stream": True}
            ) as res:
                if res.status >= 400:
                    text = await res.text()
                    raise RuntimeError(f"pull failed (HTTP {res.status})" + (f": {text[:300]}" if text else ""))

                # NDJSON: one JSON object per line, and the last line may arrive
                # unterminated. Leaving the block on an error closes the
                # connection, so a failed pull doesn't keep downloading.
                buffer = b""
                async for chunk in res.content.iter_any():
                    buffer += chunk
                    *lines, buffer = buffer.split(b"\n")
                    for line in lines:
                        handle(line)
                handle(buffer)
    except aiohttp.ClientError as err:
        raise _unreachable(err) from None

    if last and last.get("status") and last["status"] != "success":
        raise RuntimeError(f'pull ended on "{last["status"]}" instead of success')
    return last


async def chat(prompt: str, history: list[dict] | None = None, model: str | None = None, images=None):
    """
    Send a prompt to an Ollama model with optional prior history and images.
    Images ride along on the newest user message as bare base64, which is what
    Ollama takes; the model has to be a vision one (llava, llama3.2-vision, ...)
    to make anything of them. Returns the reply text, or None.
    """
    if not model:
        print("[ollama] no model set")
        return None

    messages = to_chat_messages(history, prompt)
    if images:
        messages[-1]["images"] = [img["data"] for img in images]

    data = await _request(
        "/api/chat",
        method="POST",
        body={"model": model, "messages": messages, "stream": False},
        timeout=CHAT_TIMEOUT_S,
    )

    text = ((data or {}).get("message") or {}).get("content")
    if not text:
        print("[ollama] empty response:", json.dumps(data)[:300])
        return None
    return text
