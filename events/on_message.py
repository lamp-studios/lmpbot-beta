import platform
import textwrap
import traceback
import discord
from config import Config
from utils import db
from utils import gemini

config = Config()


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

        # chatbot channel: reply with gemini
        chatbot_ch = await db.get_guild_var(guild_id, "chatbot_channel")
        if chatbot_ch and str(message.channel.id) == chatbot_ch:
            loading = await message.channel.send("Loading... <a:CircleLoader:1492857500637335685>")
            reply = await gemini.chat(message.content)
            if reply is None:
                await loading.edit(content="Gemini API key not configured or request failed.")
                return
            chunks = textwrap.wrap(reply, 2000, break_long_words=False, break_on_hyphens=False)
            if chunks:
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
            embed = discord.Embed(title="Bot Information", color=discord.Color.random())
            embed.add_field(name="Ping", value=f"{round(bot.latency * 1000)}ms")
            embed.add_field(name="Uptime", value="use /help for more")
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
