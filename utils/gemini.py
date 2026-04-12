import json
import random
import uuid
import urllib.parse
import aiohttp

_BASE = "https://gemini.google.com"
_STREAM_URL = f"{_BASE}/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate"
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
)
_MODEL_ID = "fbb127bbb056c959"  # gemini 2.0 flash

_session: aiohttp.ClientSession | None = None
_nid_cookie: str = ""


async def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session


def _build_payload(prompt: str, c="", r="", rc="", convoid="") -> str:
    inner = json.dumps([
        [[prompt, 0, None, None, None, None, 0]],
        ["en"],
        [c, r, rc, None, None, None, None, None, None, convoid],
        "",
        "",
    ])
    return urllib.parse.urlencode({"f.req": json.dumps([None, inner])})


def _extract_text(raw: str) -> str | None:
    """Parse the streaming response and pull the generated text."""
    entries = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, list):
            entries.append(data)

    # iterate in reverse so the latest wrb.fr response wins
    for data in reversed(entries):
        if not data or not isinstance(data[0], list):
            continue
        entry = data[0]
        if len(entry) < 3 or entry[0] != "wrb.fr" or not entry[2]:
            continue

        try:
            inner = json.loads(entry[2])
        except (json.JSONDecodeError, ValueError):
            continue

        # try the standard text path
        try:
            text = inner[4][0][1][0]
            if isinstance(text, list):
                text = text[0]
            if isinstance(text, str) and text.strip():
                return text
        except (IndexError, TypeError, KeyError):
            continue

    return None


async def chat(prompt: str) -> str | None:
    global _nid_cookie

    session = await _get_session()
    reqid = random.randint(1_000_000, 9_999_999)

    headers = {
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
        "Origin": _BASE,
        "Referer": _BASE,
        "User-Agent": _USER_AGENT,
        "x-goog-ext-525001261-jspb": (
            f'[1,null,null,null,"{_MODEL_ID}",null,null,0,[4],null,null,1]'
        ),
        "x-goog-ext-525005358-jspb": f'["{uuid.uuid4().hex.upper()}", 1]',
        "x-goog-ext-73010989-jspb": "[0]",
        "x-goog-ext-73010990-jspb": "[0]",
        "x-same-domain": "1",
    }

    if _nid_cookie:
        headers["Cookie"] = f"NID={_nid_cookie}"

    body = _build_payload(prompt)

    try:
        async with session.post(
            f"{_STREAM_URL}?hl=en&rt=c&_reqid={reqid}",
            data=body,
            headers=headers,
        ) as resp:
            if resp.status != 200:
                return None

            # track NID cookie for session continuity
            for cookie in resp.cookies.values():
                if cookie.key == "NID":
                    _nid_cookie = cookie.value

            raw = await resp.text()
            return _extract_text(raw)
    except Exception:
        return None
