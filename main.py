import discord
import importlib
import pkgutil
from discord import app_commands
from config import Config
from utils import db

config = Config()


class Client(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)
        self.owner_ids: set[int] = set()

    async def setup_hook(self):
        app = await self.application_info()

        if app.team is not None:
            self.owner_ids = {member.id for member in app.team.members}
        else:
            self.owner_ids = {app.owner.id}

        await db.init_db()

        self.load_modules("commands", self.tree)
        self.load_modules("events", self)

    def load_modules(self, package_name: str, target):
        package = importlib.import_module(package_name)

        for module_info in pkgutil.iter_modules(package.__path__):
            module = importlib.import_module(f"{package.__name__}.{module_info.name}")

            if hasattr(module, "setup"):
                module.setup(target)
                print(f"Loaded {package_name} module: {module_info.name}")


client = Client()
client.run(config.token)
