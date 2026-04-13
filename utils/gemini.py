import aiohttp
from config import Config

config = Config()

_MODEL = "gemini-2.5-flash"
_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{_MODEL}:generateContent"

_session: aiohttp.ClientSession | None = None


async def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session


async def chat(prompt: str) -> str | None:
    if not config.gemini_api_key:
        print("[gemini] GEMINI_API_KEY not set in .env", flush=True)
        return None

    session = await _get_session()
    body = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        async with session.post(
            _URL,
            params={"key": config.gemini_api_key},
            json=body,
        ) as resp:
            text = await resp.text()
            if resp.status != 200:
                print(f"[gemini] HTTP {resp.status}: {text[:500]}", flush=True)
                return None
            data = await resp.json(content_type=None)
    except Exception as e:
        print(f"[gemini] request exception: {e!r}", flush=True)
        return None

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        print(f"[gemini] unexpected response shape: {str(data)[:500]}", flush=True)
        return None
