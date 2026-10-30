import asyncio
import math
from urllib.parse import urlsplit

import aiohttp

from config import config

INTERVAL_S = 60


def _normalize_kuma_url(raw):
    """
    Strip any pre-existing query string so we don't double up params and
    confuse Kuma (duplicate keys get parsed as arrays/objects -> wrong status).
    """
    if not raw:
        return None
    try:
        u = urlsplit(raw)
        if u.scheme and u.netloc:
            return f"{u.scheme}://{u.netloc}{u.path}"
    except ValueError:
        pass
    return raw.split("?")[0]


PUSH_URL = _normalize_kuma_url(config.kuma_push_url)
PUSHGATEWAY_URL = config.pushgateway_url or None

print(f"[heartbeat] module loaded, PUSH_URL set: {bool(PUSH_URL)}, PUSHGATEWAY set: {bool(PUSHGATEWAY_URL)}")

_task: asyncio.Task | None = None


def ping_ms(bot) -> int:
    """Gateway latency in whole ms, or 0 before the first heartbeat."""
    latency = bot.latency
    if latency is None or not math.isfinite(latency) or latency < 0:
        return 0
    return round(latency * 1000)


async def _push(bot, session: aiohttp.ClientSession):
    ping = ping_ms(bot)
    ready = bot.is_ready()

    # Uptime Kuma push
    if PUSH_URL:
        msg = "ready" if ready else "connecting"
        params = {"status": "up", "msg": msg, "ping": str(ping)}
        try:
            async with session.get(PUSH_URL, params=params) as res:
                print(f"[heartbeat] push -> HTTP {res.status} (msg={msg}, ping={ping})")
        except Exception as err:
            print(f"[heartbeat] push failed: {err!r}")

    # Prometheus Pushgateway push (independent of Kuma)
    if PUSHGATEWAY_URL:
        body = (
            "# TYPE lmpbot_up gauge\n"
            f"lmpbot_up {1 if ready else 0}\n"
            "# TYPE lmpbot_ping_ms gauge\n"
            f"lmpbot_ping_ms {ping}\n"
        )
        try:
            url = f"{PUSHGATEWAY_URL.rstrip('/')}/metrics/job/lmpbot"
            async with session.post(url, data=body) as res:
                print(f"[heartbeat] pushgateway -> HTTP {res.status}")
        except Exception as err:
            print(f"[heartbeat] pushgateway push failed: {err!r}")


async def _loop(bot):
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        while True:
            try:
                await _push(bot, session)
            except Exception:
                pass
            await asyncio.sleep(INTERVAL_S)


def start_heartbeat(bot):
    """Start the monitoring heartbeat loop. No-op if neither endpoint is configured."""
    global _task
    if not PUSH_URL and not PUSHGATEWAY_URL:
        print("[heartbeat] no KUMA_PUSH_URL or PUSHGATEWAY_URL set; heartbeat disabled")
        return
    if _task is None or _task.done():
        _task = asyncio.create_task(_loop(bot))
