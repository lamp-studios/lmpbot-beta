import asyncio
import math
import re
import time

import discord
from discord.ext import commands

from config import config
from utils import ai, gemini, ollama, openai
from utils.owner import is_bot_owner

# how often the download progress message is edited (Discord rate limits edits)
PROGRESS_EDIT_S = 6

# model ids the chat endpoint can't use, kept out of the autocomplete list
NON_CHAT = re.compile(r"embed|whisper|tts|audio|image|dall-e|moderation|transcribe|realtime|sora", re.I)

# fire-and-forget progress edits, kept referenced until they finish
_background: set[asyncio.Task] = set()


def format_bytes(n) -> str:
    if not isinstance(n, (int, float)) or not math.isfinite(n) or n <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = min(int(math.floor(math.log(n) / math.log(1024))), len(units) - 1)
    return f"{n / 1024 ** i:.{0 if i == 0 else 1}f} {units[i]}"


def progress_line(model: str, evt: dict) -> str:
    status = (evt or {}).get("status") or "working"
    total = (evt or {}).get("total") or 0
    completed = (evt or {}).get("completed")
    if total > 0 and isinstance(completed, (int, float)) and completed >= 0:
        pct = min(100, math.floor(completed / total * 100))
        return f"Installing `{model}`: {status} {pct}% ({format_bytes(completed)} / {format_bytes(total)})"
    return f"Installing `{model}`: {status}..."


def ollama_host() -> str:
    return config.ollama_host or "http://127.0.0.1:11434"


def scope_text(scope: str) -> str:
    """"for this server" / "as the global default", for reply text."""
    return "as the global default for every server" if scope == "global" else "for this server"


async def report(ctx: discord.ApplicationContext, content: str):
    """
    Edit the deferred reply, falling back to a channel message once the
    interaction token has expired. A big model pull can outlast the 15 minute
    window, and the result still needs to reach whoever ran the command.
    """
    try:
        await ctx.edit(content=content)
    except Exception:
        try:
            await ctx.channel.send(
                f"<@{ctx.author.id}> {content}",
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, roles=False, users=[ctx.author], replied_user=False
                ),
            )
        except Exception:
            pass


async def health_note(provider: str):
    """Warn about the things that stop a provider replying, if any apply."""
    if provider == "gemini" and not config.gemini_api_key:
        return "Heads up: `GEMINI_API_KEY` isn't set on the bot, so replies will fail."
    if provider == "openai" and not openai.has_key():
        return "Heads up: `OPENAI_API_KEY` isn't set on the bot, so replies will fail."
    if provider == "ollama" and not await ollama.reachable():
        return f"Heads up: the Ollama server at `{ollama_host()}` isn't reachable, so replies will fail."
    return None


async def show_current(ctx: discord.ApplicationContext):
    current = await ai.get_settings(ctx.guild.id if ctx.guild else None)
    global_ = await ai.get_global_settings()

    source = {
        "server": "set for this server",
        "global": "the global default",
    }.get(current["scope"], "the built-in default")

    lines = [f"This server is on **{ai.label(current['provider'], current['model'])}** ({source})."]
    if current["scope"] == "server":
        lines.append(
            f"The global default is **{ai.label(global_['provider'], global_['model'])}**"
            + (" (built in)." if global_["scope"] == "default" else ".")
        )

    note = await health_note(current["provider"])
    if note:
        lines.append(note)

    lines.extend(
        [
            "",
            "Change it with `/setchatbotai provider:<gemini|openai|ollama> model:<name> scope:<server|global>`.",
            "`scope` defaults to this server only. Pick `clear` to drop this server back to the global default.",
        ]
    )

    await ctx.respond("\n".join(lines), ephemeral=True)


async def clear_override(ctx: discord.ApplicationContext):
    await ai.clear_settings(ctx.guild.id)
    now = await ai.get_settings(ctx.guild.id)
    await ctx.respond(
        "Cleared this server's override. It now follows "
        f"{'the global default' if now['scope'] == 'global' else 'the built-in default'}: "
        f"**{ai.label(now['provider'], now['model'])}**.",
        ephemeral=True,
    )


async def set_gemini(ctx, target_id, scope, model):
    await ai.set_settings(target_id, "gemini", model)

    lines = [f"Chatbot AI set to **{ai.label('gemini', model or gemini.DEFAULT_MODEL)}** {scope_text(scope)}."]
    if not model:
        lines.append(f"No model given, so the default `{gemini.DEFAULT_MODEL}` is used.")
    note = await health_note("gemini")
    if note:
        lines.append(note)

    await ctx.respond("\n".join(lines), ephemeral=True)


async def set_openai(ctx, target_id, scope, model):
    if not model:
        await ctx.respond(
            "OpenAI needs a model name, e.g. `/setchatbotai provider:openai model:gpt-4o-mini`. "
            "The model option autocompletes with whatever the bot's API key can see.",
            ephemeral=True,
        )
        return
    if not openai.has_key():
        await ctx.respond(
            "`OPENAI_API_KEY` isn't set on the bot, so OpenAI can't be used yet. "
            "Add it to the bot's `.env` and restart, then run this again.",
            ephemeral=True,
        )
        return

    await ctx.defer(ephemeral=True)

    # "unknown" means the endpoint won't list models, so the name can't be checked
    known = await openai.has_model(model)
    if known is False:
        await report(
            ctx,
            f"The API key can't see a model called `{model}`. Check the name (the `model` "
            "option autocompletes with the ones it can use). The chatbot AI has been left as it was.",
        )
        return

    await ai.set_settings(target_id, "openai", model)
    await report(
        ctx,
        f"Chatbot AI set to **{ai.label('openai', model)}** {scope_text(scope)}."
        + (
            "\nCouldn't check that model against the API, so it's set as given; watch the first reply."
            if known == "unknown"
            else ""
        ),
    )


async def set_ollama(ctx, target_id, scope, model):
    if not model:
        await ctx.respond(
            "Ollama needs a model name, e.g. `/setchatbotai provider:ollama model:llama3`. "
            "Anything from <https://ollama.com/library> works; it gets installed automatically.",
            ephemeral=True,
        )
        return

    # pulling a model takes minutes, so claim the interaction before anything else
    await ctx.defer(ephemeral=True)

    if not await ollama.reachable():
        await report(
            ctx,
            f"Can't reach the Ollama server at `{ollama_host()}`. "
            "Start it with `ollama serve` on the bot's host (install it from <https://ollama.com/download>), "
            "or point `OLLAMA_HOST` at wherever it runs, then try again.",
        )
        return

    try:
        installed = await ollama.has_model(model)
    except Exception as err:
        await report(ctx, f"Couldn't check the installed models: {err}")
        return

    if not installed:
        await report(ctx, f"Installing `{model}`, this can take a while...")

        last_edit = 0.0

        def on_progress(evt):
            nonlocal last_edit
            now = time.monotonic()
            if now - last_edit < PROGRESS_EDIT_S:
                return
            last_edit = now
            # fire and forget: progress must never hold up the download. Progress
            # only ever edits the reply, so an expired token can't spam the channel.
            task = asyncio.create_task(ctx.edit(content=progress_line(model, evt)))
            task.add_done_callback(lambda t: t.cancelled() or t.exception())
            _background.add(task)
            task.add_done_callback(_background.discard)

        try:
            await ollama.pull_model(model, on_progress)
        except Exception as err:
            await report(
                ctx,
                f"Couldn't install `{model}`: {err}\n"
                "Check the name against <https://ollama.com/library>. The chatbot AI has been left as it was.",
            )
            return

    await ai.set_settings(target_id, "ollama", model)
    await report(
        ctx,
        f"Chatbot AI set to **{ai.label('ollama', model)}** {scope_text(scope)}"
        + (" (already installed)." if installed else " (model installed)."),
    )


async def autocomplete_model(ctx: discord.AutocompleteContext):
    """Suggest models the provider actually offers; typing your own is still fine."""
    if not await is_bot_owner(ctx.bot, ctx.interaction.user.id):
        return []

    raw = ctx.value or ""
    typed = raw.lower()
    provider = ctx.options.get("provider") or "gemini"

    if provider == "gemini":
        models = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]
    elif provider == "openai":
        try:
            models = [m for m in await openai.list_models() if not NON_CHAT.search(m)]
        except Exception:
            models = []
    else:
        try:
            models = await ollama.list_models()
        except Exception:
            models = []

    matches = [m for m in models if typed in m.lower()]
    choices = [discord.OptionChoice(name=m, value=m) for m in matches[:24]]

    # let them name something the list doesn't have (a new Ollama model to install)
    if raw and len(raw) <= 100 and not any(m.lower() == typed for m in models):
        choices.insert(0, discord.OptionChoice(name=f"{raw} (install)" if provider == "ollama" else raw, value=raw))
    return choices[:25]


class SetChatbotAi(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(
        name="setchatbotai",
        description="Bot owner only. Choose which AI answers in the chatbot channel.",
        default_member_permissions=discord.Permissions(administrator=True),
    )
    async def setchatbotai(
        self,
        ctx: discord.ApplicationContext,
        provider: discord.Option(
            str,
            description="Which AI to use. Leave empty to see the current one.",
            required=False,
            default=None,
            choices=[
                discord.OptionChoice(name="gemini (Google, needs GEMINI_API_KEY)", value="gemini"),
                discord.OptionChoice(name="openai (needs OPENAI_API_KEY)", value="openai"),
                discord.OptionChoice(name="ollama (local, auto-installs the model)", value="ollama"),
            ],
        ),
        model: discord.Option(
            str,
            description="Model name. Required for openai and ollama, optional for gemini.",
            required=False,
            default=None,
            autocomplete=autocomplete_model,
        ),
        scope: discord.Option(
            str,
            description="Where it applies. Defaults to this server only.",
            required=False,
            default=None,
            choices=[
                discord.OptionChoice(name="this server only", value="server"),
                discord.OptionChoice(name="global: the default for every server", value="global"),
                discord.OptionChoice(
                    name="clear this server's setting and follow the global default", value="clear"
                ),
            ],
        ),
    ):
        if not await is_bot_owner(self.bot, ctx.author.id):
            await ctx.respond("Only the bot owner can change the chatbot AI.", ephemeral=True)
            return

        model = (model or "").strip() or None
        scope = scope or "server"

        if scope != "global" and not ctx.guild:
            await ctx.respond("Run this in the server you want to change, or use `scope:global`.", ephemeral=True)
            return

        if scope == "clear":
            await clear_override(ctx)
            return
        if not provider:
            await show_current(ctx)
            return

        target_id = ai.GLOBAL_ID if scope == "global" else ctx.guild.id

        if provider == "ollama":
            await set_ollama(ctx, target_id, scope, model)
        elif provider == "openai":
            await set_openai(ctx, target_id, scope, model)
        else:
            await set_gemini(ctx, target_id, scope, model)


def setup(bot: discord.Bot):
    bot.add_cog(SetChatbotAi(bot))
