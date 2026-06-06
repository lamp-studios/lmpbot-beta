import os
from urllib.parse import urlsplit, urlunsplit
import aiohttp
import discord
from discord.ext import tasks

_RAW_URL = os.getenv("KUMA_PUSH_URL")
# Strip any pre-existing query string so we don't double up params and confuse Kuma
# (duplicate keys get parsed as arrays/objects → "[object Object]" / wrong status).
if _RAW_URL:
    _parts = urlsplit(_RAW_URL)
    PUSH_URL = urlunsplit((_parts.scheme, _parts.netloc, _parts.path, "", ""))
else:
    PUSH_URL = None
# Prometheus Pushgateway base URL, e.g. http://127.0.0.1:9094 (new monitoring stack).
PUSHGATEWAY_URL = os.getenv("PUSHGATEWAY_URL")
INTERVAL_SECONDS = 60
print(f"[heartbeat] module loaded, PUSH_URL set: {bool(PUSH_URL)}, PUSHGATEWAY set: {bool(PUSHGATEWAY_URL)}")


def setup(bot: discord.Bot):
    print("[heartbeat] setup() called")
    if not PUSH_URL and not PUSHGATEWAY_URL:
        print("[heartbeat] no KUMA_PUSH_URL or PUSHGATEWAY_URL set; heartbeat disabled")
        return

    @tasks.loop(seconds=INTERVAL_SECONDS)
    async def push_heartbeat():
        latency = bot.latency
        if latency != latency or latency in (float("inf"), float("-inf")):
            ping_ms = 0
        else:
            ping_ms = int(latency * 1000)
        # Uptime Kuma push (only if KUMA_PUSH_URL is still configured).
        if PUSH_URL:
            msg = "ready" if bot.is_ready() else "connecting"
            params = {"status": "up", "msg": msg, "ping": str(ping_ms)}
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(PUSH_URL, params=params) as resp:
                        print(f"[heartbeat] push -> HTTP {resp.status} (msg={msg}, ping={ping_ms})")
            except Exception as e:
                print(f"[heartbeat] push failed: {e!r}")

        # Also push to Prometheus Pushgateway (new monitoring stack). Independent of Kuma:
        # a failure here must not affect the Kuma heartbeat above.
        if PUSHGATEWAY_URL:
            up_val = 1 if bot.is_ready() else 0
            body = (
                "# TYPE lmpbot_up gauge\n"
                f"lmpbot_up {up_val}\n"
                "# TYPE lmpbot_ping_ms gauge\n"
                f"lmpbot_ping_ms {ping_ms}\n"
            )
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    url = f"{PUSHGATEWAY_URL.rstrip('/')}/metrics/job/lmpbot"
                    async with session.post(url, data=body) as resp:
                        print(f"[heartbeat] pushgateway -> HTTP {resp.status}")
            except Exception as e:
                print(f"[heartbeat] pushgateway push failed: {e!r}")

    @push_heartbeat.before_loop
    async def _wait():
        print("[heartbeat] waiting for bot ready before first push")
        await bot.wait_until_ready()
        print("[heartbeat] bot ready, starting push loop")

    async def _start_on_connect():
        print("[heartbeat] on_connect listener fired; is_running=", push_heartbeat.is_running())
        if not push_heartbeat.is_running():
            push_heartbeat.start()

    async def _start_on_ready():
        print("[heartbeat] on_ready listener fired; is_running=", push_heartbeat.is_running())
        if not push_heartbeat.is_running():
            push_heartbeat.start()

    bot.add_listener(_start_on_connect, "on_connect")
    bot.add_listener(_start_on_ready, "on_ready")
  
