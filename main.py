import pkgutil
import sys
import time
from pathlib import Path

import discord

from config import config
from utils.db import init_storage

ROOT = Path(__file__).resolve().parent


class LmpBot(discord.Bot):
    async def start(self, token: str, *, reconnect: bool = True) -> None:
        # storage comes up before the gateway connects, so no event can arrive
        # while the database is still unavailable
        await init_storage()
        await super().start(token, reconnect=reconnect)


intents = discord.Intents.none()
intents.guilds = True
intents.guild_messages = True
intents.members = True
intents.message_content = True

bot = LmpBot(
    intents=intents,
    # commands are synced from events/ready.py (and `.up`), not on every connect
    auto_sync_commands=False,
)
bot.start_time = time.time()
bot.owner_ids = set()


def load_dir(package: str) -> None:
    """Load every module in a package as an extension; each one has a setup(bot)."""
    for module in sorted(pkgutil.iter_modules([str(ROOT / package)]), key=lambda m: m.name):
        if module.name.startswith("_"):
            continue
        name = f"{package}.{module.name}"
        try:
            bot.load_extension(name)
            print(f"Loaded {package} module: {module.name}")
        except Exception as err:
            print(f"Skipped {name}: {err!r}")


def main() -> None:
    if not config.token:
        print("Fatal startup error: DANGER_DONTSHARETOYKEN isn't set in .env")
        sys.exit(1)

    load_dir("commands")
    load_dir("events")

    bot.run(config.token)


if __name__ == "__main__":
    main()
