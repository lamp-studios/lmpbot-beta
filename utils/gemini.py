import base64

from google import genai
from google.genai import types

from config import config

DEFAULT_MODEL = "gemini-2.5-flash"

_client = genai.Client(api_key=config.gemini_api_key) if config.gemini_api_key else None


def _content(role: str, parts: list[dict]) -> types.Content:
    return types.Content(
        role=role,
        parts=[types.Part.from_text(text=(p or {}).get("text", "") or "") for p in parts or []],
    )


async def chat(prompt: str, history: list[dict] | None = None, model: str | None = DEFAULT_MODEL, images=None):
    """
    Send a prompt to Gemini with optional prior history and images.
    `history` is [{"role", "parts": [{"text"}]}]; `images` is
    [{"mime_type", "data"}] with base64 data. Returns the reply text, or None.
    """
    if not config.gemini_api_key or _client is None:
        print("[gemini] GEMINI_API_KEY not set")
        return None

    try:
        parts = [types.Part.from_text(text=prompt)]
        for image in images or []:
            parts.append(
                types.Part.from_bytes(data=base64.b64decode(image["data"]), mime_type=image["mime_type"])
            )

        contents = [_content(h["role"], h.get("parts")) for h in history or []]
        contents.append(types.Content(role="user", parts=parts))

        result = await _client.aio.models.generate_content(model=model or DEFAULT_MODEL, contents=contents)
        return result.text
    except Exception as err:
        print("[gemini] request exception:", repr(err))
        return None
