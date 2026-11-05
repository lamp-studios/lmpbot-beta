from pathlib import Path

import discord
from aiohttp import web

from api.keys import API_KEY, BOT
from api.middleware import auth_middleware, error_middleware
from api.routes import setup_routes
from config import config

HOST = "0.0.0.0"
DEFAULT_PORT = 8080
# ports tried after the preferred one before letting the OS pick any free port
PORT_ATTEMPTS = 20
MAX_BODY_BYTES = 64 * 1024
# the port actually bound, for a tunnel or reverse proxy to read
# (database/ is gitignored and preserved across updates)
PORT_FILE = Path(__file__).resolve().parent.parent / "database" / "api-port"

_runner: web.AppRunner | None = None


def _port() -> int | None:
    raw = config.bot_api_port
    if raw is None:
        return DEFAULT_PORT
    try:
        port = int(raw)
    except ValueError:
        return None
    return port if 1 <= port <= 65535 else None


def create_app(bot: discord.Bot, api_key: str) -> web.Application:
    # error_middleware is outermost so auth failures and handler errors all come back as JSON
    app = web.Application(
        middlewares=[error_middleware, auth_middleware],
        client_max_size=MAX_BODY_BYTES,
    )
    app[BOT] = bot
    app[API_KEY] = api_key.encode()
    setup_routes(app)
    return app


def _candidate_ports(preferred: int) -> list[int]:
    """The preferred port, the next few above it, then 0 (any free port)."""
    ports = [p for p in range(preferred, preferred + PORT_ATTEMPTS) if p <= 65535]
    return ports + [0]


async def _bind(runner: web.AppRunner, preferred: int) -> int:
    """Bind the first free candidate port and return the port actually in use."""
    last_err: OSError | None = None
    for port in _candidate_ports(preferred):
        site = web.TCPSite(runner, HOST, port)
        try:
            await site.start()
        except OSError as err:
            last_err = err
            await site.stop()  # unregister the failed site from the runner
            continue
        return site._server.sockets[0].getsockname()[1]
    raise last_err or OSError("no port available")


def _write_port_file(port: int) -> None:
    try:
        PORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        PORT_FILE.write_text(f"{port}\n")
    except OSError as err:
        print(f"[api] couldn't write {PORT_FILE}: {err!r}")


async def start_api(bot: discord.Bot) -> None:
    """
    Start the HTTP API on the bot's event loop. Never raises: any problem is logged
    and the bot carries on without the API.
    """
    global _runner
    if _runner is not None:
        return

    if not config.bot_api_key:
        print("[api] BOT_API_KEY isn't set in .env; the HTTP API is disabled")
        return

    port = _port()
    if port is None:
        print("[api] BOT_API_PORT must be a number between 1 and 65535; the HTTP API is disabled")
        return

    runner = None
    try:
        # access_log=None: nothing about requests (headers included) is ever logged
        runner = web.AppRunner(create_app(bot, config.bot_api_key), access_log=None)
        await runner.setup()
        bound = await _bind(runner, port)
    except Exception as err:
        print(f"[api] failed to start on {HOST} (tried from port {port}): {err!r}")
        if runner is not None:
            try:
                await runner.cleanup()
            except Exception:
                pass
        return

    _runner = runner
    _write_port_file(bound)
    if bound != port:
        print(f"[api] port {port} was busy")
    print(f"[api] listening on {HOST}:{bound}")


async def stop_api() -> None:
    global _runner
    if _runner is None:
        return
    runner, _runner = _runner, None
    try:
        await runner.cleanup()
    except Exception as err:
        print(f"[api] error while stopping: {err!r}")
