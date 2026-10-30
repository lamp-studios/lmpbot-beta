import platform
import re
import textwrap
import time
import traceback

import discord
from discord.ext import commands

from config import config
from utils import ai
from utils.attachments import collect_images
from utils.birthdays import snowflake
from utils.db import (
    add_chat_memory,
    erased_since,
    get_chat_memory,
    get_guild_var,
    get_member_var,
    get_user_facts,
    search_guild_var,
    set_member_var,
    set_user_fact,
)
from utils.heartbeat import ping_ms
from utils.memory import build_smart_memory, extract_facts, format_uptime, split_message
from utils.mentions import describe_user, resolve_mentions
from utils.owner import is_owner_cached

# the first run of whitespace followed by anything splits a command from its args
ARGS_SPLIT = re.compile(r"\s+(.+)", re.S)


async def log_spambot(guild: discord.Guild, user: discord.abc.User):
    """
    Note a caught spambot in the guild's log channel, if one is configured.
    Entirely best-effort: a missing, deleted or unwritable log channel must never
    stop the ban, so every failure here is swallowed.
    """
    try:
        channel_id = snowflake(await get_guild_var(guild.id, "dont_talk_logging_channel"))
        if not channel_id:
            return

        channel = guild.get_channel(channel_id)
        if channel is None:
            try:
                channel = await guild.fetch_channel(channel_id)
            except Exception:
                return
        if not isinstance(channel, discord.abc.Messageable):
            return

        await channel.send(
            f"**{user.name}** (`{user.id}`, <@{user.id}>) was detected as a "
            "spambot and has been soft-banned from the server.",
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except Exception:
        pass


async def run_python(code: str, bot: discord.Bot, message: discord.Message):
    """
    Run owner-supplied code with `bot`, `client`, `message` and `discord` in
    scope. A lone expression is returned as-is; anything else runs as the body of
    an async function, so `await` works and `return` sends a value back.
    """
    env = {"bot": bot, "client": bot, "message": message, "discord": discord}
    try:
        compile(code, "<exe>", "eval")
        body = f"return ({code})"
    except SyntaxError:
        body = code

    exec(f"async def __exe():\n{textwrap.indent(body, '    ')}", env)
    return await env["__exe"]()


class MessageCreate(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        bot = self.bot
        guild = message.guild
        guild_id = guild.id

        # dont_talk channel: auto-ban anyone who messages there
        dont_talk = await get_guild_var(guild_id, "dont_talk_channel")
        if dont_talk and str(message.channel.id) == dont_talk:
            author = message.author
            try:
                # neither of these is worth losing the ban over
                try:
                    await message.delete()
                except Exception:
                    pass
                try:
                    await author.send("Bot detected!!!")
                except Exception:
                    pass

                await guild.ban(author, reason="spambot detected", delete_message_seconds=120)
                await guild.unban(author, reason="spambot detection unban system")

                # only after the soft-ban went through, so the log can't claim otherwise
                await log_spambot(guild, author)
            except Exception as err:
                if not (isinstance(err, discord.HTTPException) and err.code == 50013):
                    print("dont_talk ban failed:")
                    traceback.print_exception(type(err), err, err.__traceback__)
            return

        # chatbot channel
        chatbot_channel = await get_guild_var(guild_id, "chatbot_channel")
        if chatbot_channel and str(message.channel.id) == chatbot_channel:
            await self.chatbot_reply(message)
            return

        # prefix commands
        if not message.content.startswith(config.prefix):
            return

        rest = message.content[len(config.prefix):]
        m = ARGS_SPLIT.search(rest)
        cmd = (rest[: m.start()] if m else rest).lower()
        args = m.group(1) if m else ""

        if cmd == "ping":
            await message.channel.send(f"Pong! {ping_ms(bot)}ms")

        elif cmd == "info":
            uptime = format_uptime(time.time() - bot.start_time)
            embed = discord.Embed(title="Bot Information", color=discord.Color.random())
            embed.add_field(name="Ping", value=f"{ping_ms(bot)}ms", inline=False)
            embed.add_field(name="Uptime", value=uptime, inline=False)
            embed.add_field(name="OS", value=platform.system() or "Unknown", inline=False)
            await message.channel.send(embed=embed)

        elif cmd == "verify":
            enabled = await get_guild_var(guild_id, "verification_enabled")
            if not enabled:
                await message.channel.send("Verification is not enabled on this server.", delete_after=2)
                return
            verified = await get_member_var(guild_id, message.author.id, "is_verified")
            if verified == "true":
                await message.channel.send("You are already verified!")
                return
            await set_member_var(guild_id, message.author.id, "is_verified", "true")

            role_id = snowflake(await get_guild_var(guild_id, "verification_role"))
            role = guild.get_role(role_id) if role_id else discord.utils.get(guild.roles, name="verified")
            if role:
                await message.author.add_roles(role)

            await message.channel.send("Verified successfully!")

        elif cmd == "up":
            if not is_owner_cached(bot, message.author.id):
                return
            from utils.deploy import register_commands

            await register_commands(bot)
            await message.add_reaction("\N{THUMBS UP SIGN}\N{EMOJI MODIFIER FITZPATRICK TYPE-1-2}")

        elif cmd == "exe":
            if not is_owner_cached(bot, message.author.id):
                return
            if not args:
                return
            try:
                result = await run_python(args, bot, message)
                if result is not None:
                    await message.channel.send(str(result)[:2000])
            except Exception as err:
                trace = "".join(traceback.format_exception(type(err), err, err.__traceback__))
                await message.channel.send("```\n" + trace[-1900:] + "\n```")

        elif cmd == "send_new":
            if not is_owner_cached(bot, message.author.id):
                return
            if not args:
                return
            for row in await search_guild_var("news_channel"):
                channel_id = snowflake(row["value"])
                if not channel_id:
                    continue
                channel = bot.get_channel(channel_id)
                if channel is None:
                    try:
                        channel = await bot.fetch_channel(channel_id)
                    except Exception:
                        channel = None
                if channel:
                    await channel.send(args[:2000])

    async def chatbot_reply(self, message: discord.Message):
        guild = message.guild
        guild_id = guild.id
        author = message.author

        # nothing the model can work with (a sticker or an embed on its own)
        if not message.content.strip() and not message.attachments:
            return

        # a /delete_data that lands while this reply is in flight has to win, so
        # every write below checks the user wasn't wiped since the message came in
        started_at = int(time.time() * 1000)

        def erased():
            return erased_since(author.id, started_at)

        loading = await message.channel.send("Loading... <a:CircleLoader:1492857500637335685>")

        # BUILD THE PROMPT: mentions become names the model understands, and any
        # images are downloaded and described in the text as well as sent along
        images, notes = await collect_images(message.attachments)
        resolved = await resolve_mentions(message.content, message, self.bot)
        prompt = "\n".join(part for part in [resolved, *notes] if part)

        # SAVE USER MESSAGE + FETCH HISTORY
        # the resolved text is what gets stored, so old turns stay readable
        if not erased():
            await add_chat_memory(guild_id, message.channel.id, author.id, "user", prompt)

        rows = await get_chat_memory(guild_id, message.channel.id, author.id, 50)
        transcript = build_smart_memory(rows)

        history = []
        if transcript:
            history.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": "The following is our chat history so far (oldest to newest), for context:\n\n"
                            + transcript
                        }
                    ],
                }
            )

        facts = extract_facts(resolved)
        for key, value in facts.items():
            if len(value) > 2 and not erased():
                await set_user_fact(guild_id, author.id, key, value)

        user_facts = await get_user_facts(guild_id, author.id)
        if user_facts:
            fact_text = "\n".join(f"{k}: {v}" for k, v in user_facts.items())
            history.insert(0, {"role": "user", "parts": [{"text": f"User facts:\n{fact_text}"}]})

        # who is speaking, and how to read the mentions in what follows
        member = author if isinstance(author, discord.Member) else None
        history.insert(
            0,
            {
                "role": "user",
                "parts": [
                    {
                        "text": f"You are talking to {describe_user(author, member)} "
                        f'in the Discord server "{guild.name}". People are written as '
                        "@username (display name, id: 123456789); mention someone back with <@their id>."
                    }
                ],
            },
        )

        # CALL THE GUILD'S CHATBOT AI (Gemini by default, see /setchatbotai)
        try:
            result = await ai.chat(guild_id, prompt, history, images)
        except Exception as err:
            await loading.edit(content=f"Chatbot failed. {str(err)[:1900]}")
            return

        reply = result["text"]
        if reply is None:
            await loading.edit(content=f"{result['label']} failed.")
            return

        # SAVE BOT RESPONSE (still sent below even if the user was wiped meanwhile)
        if not erased():
            await add_chat_memory(guild_id, message.channel.id, author.id, "model", reply)

        # SEND RESPONSE
        # The model is told it can mention people, and anyone can ask it to
        # mention anyone, so pings are limited to whoever is already in this
        # exchange. Everything else renders as a name without notifying.
        allowed_mentions = discord.AllowedMentions(
            everyone=False,
            roles=False,
            users=[author, *message.mentions],
            replied_user=False,
        )
        chunks = split_message(reply, 2000)
        await loading.edit(content=chunks[0], allowed_mentions=allowed_mentions)
        for chunk in chunks[1:]:
            await message.channel.send(chunk, allowed_mentions=allowed_mentions)


def setup(bot: discord.Bot):
    bot.add_cog(MessageCreate(bot))
