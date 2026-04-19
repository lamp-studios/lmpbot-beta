import platform
import textwrap
import time
import traceback
import discord
from config import Config
from utils import db
from utils import gemini
import aiosqlite
from utils.db import DB_PATH

config = Config()

def extract_facts(content: str):
    content = content.lower()
    facts = {}

    if "my name is " in content:
        facts["name"] = content.split("my name is ")[1].split()[0]

    if "i am " in content:
        facts["identity"] = content.split("i am ")[1][:50]

    if "i like " in content:
        facts["likes"] = content.split("i like ")[1][:50]

    if "i hate " in content:
        facts["hates"] = content.split("i hate ")[1][:50]

    if "i am building " in content:
        facts["project"] = content.split("i am building ")[1][:80]

    return facts

def score_message(content: str) -> int:
    content_lower = content.lower()

    score = 0

    # length = more likely important
    score += min(len(content) // 50, 10)

    # keywords (customize these for your bot)
    important_keywords = [
        "remember", "important", "note", "my name is",
        "i am", "i like", "i hate", "always", "never",
        "project", "server", "api", "password", "token"
    ]

    for word in important_keywords:
        if word in content_lower:
            score += 5

    # penalize garbage
    spammy = ["lol", "lmao", "ok", "k", "hi", "hello", "😂", "💀"]
    if content_lower.strip() in spammy:
        score -= 5

    return score

def compress_text(text: str, max_len: int) -> str:
    text = text.strip()

    if len(text) <= max_len:
        return text

    # keep start + end (important context usually lives there)
    half = max_len // 2
    return text[:half] + " ... " + text[-half:]

def build_smart_memory(rows):
    """
    rows = [(role, content), ...] newest last
    """

    scored = []

    # score all messages
    for role, content in rows:
        s = score_message(content)
        scored.append((role, content, s))

    # sort by importance (but keep some recency)
    scored_sorted = sorted(
        enumerate(scored),
        key=lambda x: (x[1][2], x[0]),  # (score, recency index)
        reverse=True
    )

    selected = []
    total_chars = 0

    for idx, (role, content, score) in [x[1] for x in scored_sorted]:
        # compression strength based on score
        if score >= 10:
            limit = 1200
        elif score >= 5:
            limit = 500
        elif score >= 0:
            limit = 200
        else:
            limit = 80  # trash gets nuked

        compressed = compress_text(content, limit)

        if total_chars + len(compressed) > 7000:
            continue

        selected.append((idx, role, compressed))
        total_chars += len(compressed)

    # restore chronological order
    selected.sort(key=lambda x: x[0])

    return [{"role": r, "parts": [{"text": c}]} for _, r, c in selected]


def _format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    weeks, seconds = divmod(seconds, 7 * 24 * 3600)
    days, seconds = divmod(seconds, 24 * 3600)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []
    if weeks:
        parts.append(f"{weeks}w")
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)


def setup(bot: discord.Bot):
    @bot.event
    async def on_message(message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        guild_id = message.guild.id

        # dont_talk channel: auto-ban anyone who messages there
        dont_talk = await db.get_guild_var(guild_id, "dont_talk_channel")
        if dont_talk and str(message.channel.id) == dont_talk:
            try:
                await message.delete()
                await message.author.send("Bot detected!!!")
                await message.guild.ban(message.author, reason="spambot detected", delete_message_seconds=120)
                await message.guild.unban(message.author, reason="spambot detection unban system")
            except discord.Forbidden:
                pass
            return

	# chatbot channel
	chatbot_ch = await db.get_guild_var(guild_id, "chatbot_channel")
	if chatbot_ch and str(message.channel.id) == chatbot_ch:
	    loading = await message.channel.send("Loading... <a:CircleLoader:1492857500637335685>")
	
	    # SAVE USER MESSAGE + FETCH HISTORY
	    async with aiosqlite.connect(DB_PATH) as conn:
	        await conn.execute(
	            "INSERT INTO chat_memory (guild_id, channel_id, user_id, role, content) VALUES (?, ?, ?, ?, ?)",
	            (guild_id, message.channel.id, message.author.id, "user", message.content)
	        )
    
			cursor = await conn.execute("""
				    SELECT role, content FROM chat_memory
				    WHERE guild_id = ? AND channel_id = ? AND user_id = ?
				    AND (user_id = ? OR user_id = 0)
				    ORDER BY timestamp DESC
				    LIMIT 10
				""", (guild_id, message.channel.id, message.author.id))	
	        rows = await cursor.fetchall()
	        await conn.commit()
        max_chars = 6000 - len(message.content)
	    history = build_smart_memory(rows)
        facts = extract_facts(message.content)

        for k, v in facts.items():
            if len(v) > 2:
                await db.set_user_fact(guild_id, message.author.id, k, v)
        
        user_facts = await db.get_user_facts(guild_id, message.author.id)

        if user_facts:
            fact_text = "\n".join([f"{k}: {v}" for k, v in user_facts.items()])

            history.insert(0, {
                "role": "user",
                "parts": [{"text": f"User facts:\n{fact_text}"}]
            })
        
	    # CALL GEMINI
	    reply = await gemini.chat(message.content, history)
	
	    if reply is None:
	        await loading.edit(content="Gemini failed.")
	        return
	
	    # SAVE BOT RESPONSE
	    async with aiosqlite.connect(DB_PATH) as conn:
	        await conn.execute(
	            "INSERT INTO chat_memory (guild_id, channel_id, user_id, role, content) VALUES (?, ?, ?, ?, ?)",
	            (guild_id, message.channel.id, message.author.id, "model", reply)
	        )
	        await conn.commit()
	
	    # SEND RESPONSE
	    chunks = textwrap.wrap(reply, 2000, break_long_words=False, break_on_hyphens=False)
	
	    await loading.edit(content=chunks[0])
	    for chunk in chunks[1:]:
	        await message.channel.send(chunk)
	
	    return
        # prefix commands
        if not message.content.startswith(config.prefix):
            return

        parts = message.content[len(config.prefix):].split(None, 1)
        cmd = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "ping":
            await message.channel.send(f"Pong! {round(bot.latency * 1000)}ms")

        elif cmd == "info":
            uptime = _format_uptime(time.time() - bot.start_time)
            embed = discord.Embed(title="Bot Information", color=discord.Color.random())
            embed.add_field(name="Ping", value=f"{round(bot.latency * 1000)}ms")
            embed.add_field(name="Uptime", value=uptime)
            embed.add_field(name="OS", value=platform.system())
            await message.channel.send(embed=embed)

        elif cmd == "verify":
            verified = await db.get_member_var(guild_id, message.author.id, "is_verified")
            if verified == "true":
                await message.channel.send("You are already verified!")
                return
            await db.set_member_var(guild_id, message.author.id, "is_verified", "true")
            role_id = await db.get_guild_var(guild_id, "verification_role")
            if role_id is None:
                role = discord.utils.get(message.guild.roles, name="verified")
            else:
                role = message.guild.get_role(int(role_id))
            if role:
                await message.author.add_roles(role)
            await message.channel.send("Verified successfully!")

        elif cmd == "up":
            if not await bot.is_owner(message.author):
                return
            await bot.sync_commands()
            await message.add_reaction("\U0001f44d\U0001f3fb")

        elif cmd == "exe":
            if not await bot.is_owner(message.author):
                return
            if not args:
                return
            try:
                exec_globals = {"bot": bot, "client": bot, "message": message, "discord": discord}
                exec(f"import asyncio\nasync def _ex():\n{textwrap.indent(args, '    ')}", exec_globals)
                result = await exec_globals["_ex"]()
                if result is not None:
                    await message.channel.send(str(result)[:2000])
            except Exception:
                await message.channel.send(f"```\n{traceback.format_exc()[:1900]}\n```")

        elif cmd == "send_new":
            if not await bot.is_owner(message.author):
                return
            rows = await db.search_guild_var("news_channel")
            for _, channel_id in rows:
                ch = bot.get_channel(int(channel_id))
                if ch:
                    await ch.send(args[:2000])
