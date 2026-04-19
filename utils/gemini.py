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


async def chat(prompt: str, history: list = None) -> str | None:
    if not config.gemini_api_key:
        print("[gemini] GEMINI_API_KEY not set", flush=True)
        return None

    session = await _get_session()

    contents = history[:] if history else []
    contents.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })

    body = {"contents": contents}

    try:
        async with session.post(
            _URL,
            params={"key": config.gemini_api_key},
            json=body,
        ) as resp:
            text = await resp.text()

            if resp.status != 200:
                print(f"[gemini] HTTP {resp.status}: {text[:500]}")
                return None

            data = await resp.json(content_type=None)

    except Exception as e:
        print(f"[gemini] request exception: {e!r}")
        return None

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except:
        print(f"[gemini] bad response: {str(data)[:500]}")
        return None