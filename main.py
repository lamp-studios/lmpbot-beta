import discord
import importlib
import pkgutil
from config import Config
from utils import db

config = Config()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Bot(intents=intents)


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
