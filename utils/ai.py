# Chatbot provider router.
#
# Which AI answers is a bot-owner setting with two scopes: a global default
# used by every server, and a per-server override on top of it. Lookups go
# server -> global -> Gemini, so a server that was never touched keeps the
# original behaviour, and clearing an override drops that server back to the
# global default rather than to nothing.
#
# The global row is stored as a guild var under the id "global". Guild ids are
# numeric snowflakes, so it can't collide with a real server.

from utils import gemini, ollama, openai
from utils.db import delete_guild_var, get_guild_var, set_guild_var

PROVIDER_KEY = "chatbot_ai"
MODEL_KEY = "chatbot_ai_model"
GLOBAL_ID = "global"

PROVIDERS = ["gemini", "openai", "ollama"]
DEFAULT_PROVIDER = "gemini"

NAMES = {"gemini": "Gemini", "openai": "OpenAI", "ollama": "Ollama"}


def _default_model(provider):
    """Only Gemini has a usable default; the others are meaningless without a model."""
    return gemini.DEFAULT_MODEL if provider == "gemini" else None


async def _read_scope(scope_id):
    provider = await get_guild_var(scope_id, PROVIDER_KEY)
    if not provider or provider not in PROVIDERS:
        return None
    model = await get_guild_var(scope_id, MODEL_KEY)
    return {"provider": provider, "model": model or _default_model(provider)}


async def get_settings(guild_id):
    """
    The AI in effect for a guild, and where the setting came from:
    "server" (this guild's override), "global" (the owner's default for every
    guild) or "default" (nothing configured anywhere).
    Returns {"provider", "model", "scope"}.
    """
    server = await _read_scope(guild_id) if guild_id else None
    if server:
        return {**server, "scope": "server"}

    return await get_global_settings()


async def get_global_settings():
    """The global default on its own, ignoring any server override."""
    global_ = await _read_scope(GLOBAL_ID)
    if global_:
        return {**global_, "scope": "global"}
    return {"provider": DEFAULT_PROVIDER, "model": _default_model(DEFAULT_PROVIDER), "scope": "default"}


async def set_settings(scope_id, provider, model):
    """
    Write a setting. `scope_id` is a guild id for a server override, or
    GLOBAL_ID for the default every server falls back to.
    """
    await set_guild_var(scope_id, PROVIDER_KEY, provider)
    if model:
        await set_guild_var(scope_id, MODEL_KEY, model)
    else:
        await delete_guild_var(scope_id, MODEL_KEY)


async def clear_settings(scope_id):
    """Drop a server's override so it follows the global default again."""
    await delete_guild_var(scope_id, PROVIDER_KEY)
    await delete_guild_var(scope_id, MODEL_KEY)


def label(provider, model):
    """Human-readable name for replies and error messages."""
    name = NAMES.get(provider, provider)
    return f"{name} ({model})" if model else name


async def chat(guild_id, prompt, history=None, images=None):
    """
    Send a prompt to whichever provider the guild is on.
    `text` is None when the provider failed softly (see the bot logs); anything
    worth telling the user about is raised with a message they can act on.
    Returns {"text", "provider", "model", "scope", "label"}.
    """
    settings = await get_settings(guild_id)
    provider, model = settings["provider"], settings["model"]

    if provider == "ollama":
        text = await ollama.chat(prompt, history, model, images)
    elif provider == "openai":
        text = await openai.chat(prompt, history, model, images)
    else:
        text = await gemini.chat(prompt, history, model, images)

    return {**settings, "text": text, "label": label(provider, model)}
