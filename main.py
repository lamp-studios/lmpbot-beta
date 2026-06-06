import time
import discord
import importlib
import pkgutil
from config import Config
from utils import db

# py-cord auto-fetches "default sounds" during _delay_ready; that endpoint is
# rate-limited per-bot and a 429 there raises through, blocking on_ready
# indefinitely. Default sounds are cosmetic — swallow HTTPExceptions there.
import discord.state as _ds
_orig_add_default_sounds = _ds.ConnectionState._add_default_sounds
async def _safe_add_default_sounds(self):
    try:
        return await _orig_add_default_sounds(self)
    except discord.errors.HTTPException as e:
        print(f"[patch] skipping _add_default_sounds: {e}")
_ds.ConnectionState._add_default_sounds = _safe_add_default_sounds

config = Config()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Bot(intents=intents)
bot.start_time = time.time()


@bot.event
async def on_connect():
    await db.init_db()


def load_modules(package_name: str):
    package = importlib.import_module(package_name)
    for module_info in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package.__name__}.{module_info.name}")
        if hasattr(module, "setup"):
            module.setup(bot)
            print(f"Loaded {package_name} module: {module_info.name}")


load_modules("commands")
load_modules("events")

bot.run(config.token)

