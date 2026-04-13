import aiohttp
from config import Config

config = Config()

_MODEL = "gemini-2.0-flash"
_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{_MODEL}:generateContent"

_session: aiohttp.ClientSession | None = None


async def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session


async def chat(prompt: str) -> str | None:
    if not config.gemini_api_key:
        return None

    session = await _get_session()
    body = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        async with session.post(
            _URL,
            params={"key": config.gemini_api_key},
            json=body,
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
    except Exception:
        return None

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        return None
