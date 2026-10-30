# AGENTS.md - Codebase Guidelines for AI Agents

## Project Overview

This is **lmpbot-beta**, a Discord bot built with [Pycord](https://pycord.dev) (`py-cord` 2.8+).
Storage is a tiered fallback (MongoDB -> Supabase -> Neon -> Turso -> local SQLite), the chatbot runs on
Gemini (`google-genai`), with OpenAI and a local Ollama server as alternatives chosen
globally or per guild, and the bot supports both prefix commands (`.`) and slash commands.

## File Structure

```
lmpbot-beta/
├── main.py                     # Entry point: Bot setup, intents, extension loader, storage init
├── config.py                   # Env/config loader (reads .env via python-dotenv)
├── requirements.txt            # Python dependencies
├── start.bat                   # Windows launcher (creates .venv, installs, runs)
├── setup-lmpbot.sh             # Raspberry Pi / Linux installer (venv + systemd + auto-updater)
├── supabase-schema.sql         # Tables for the Supabase fallback tier (Neon creates the same on start)
├── neon.ts, package.json       # Neon infra config for `neon deploy` (Postgres only); the bot never runs it
├── .env                        # Bot token, AI keys, storage URIs (never committed)
│
├── commands/                   # Slash commands (auto-loaded; one cog per file)
│   ├── help.py                 # /help
│   ├── birthday.py             # /birthday - birthday announcements and roles
│   ├── lockdown.py             # /lockdown - hide every channel bar one
│   ├── undolockdown.py         # /undolockdown - restore what /lockdown changed
│   ├── members.py              # /members - show verified members
│   ├── welcome.py              # /welcome - mass welcome sender
│   ├── delete_data.py          # /delete_data - owner only; wipe one user's stored data
│   ├── set_chatbot_channel.py  # /set_chatbot_channel
│   ├── setchatbotai.py         # /setchatbotai - owner only; pick Gemini/OpenAI/Ollama, per guild or global
│   ├── set_bot_channel.py      # /set_bot_channel
│   ├── set_forum_channel.py    # /set_forum_channel
│   ├── set_news_channel.py     # /set_news_channel
│   └── set_verification_role.py# /set_verification_role
│
├── events/                     # Event listeners (auto-loaded; one cog per file)
│   ├── ready.py                # on_ready - startup log, owner resolution, command sync, status loop
│   ├── message_create.py       # on_message - prefix commands, dont_talk auto-ban, chatbot replies
│   ├── interaction_create.py   # slash command error replies + "learnmore" button
│   ├── guild_create.py         # on_guild_join log
│   └── thread_create.py        # Forum channel: auto-add staff to new threads
│
├── utils/
│   ├── db.py                   # storage router + guild/member/fact/chat helpers
│   ├── backends/               # mongo.py, supabase.py, neon.py, turso.py, sqlite.py (+ timestamps.py)
│   ├── birthdays.py            # birthday config keys, date helpers, daily scheduler
│   ├── lockdown.py             # lockdown state, apply/restore of a role's View Channel
│   ├── ai.py                   # chatbot provider router (server override -> global -> Gemini)
│   ├── gemini.py               # Gemini chat helper (google-genai, async)
│   ├── openai.py               # OpenAI chat helper, over the Chat Completions HTTP API
│   ├── ollama.py               # Ollama chat helper + model install, over its HTTP API
│   ├── owner.py                # bot owner ids (single owner or dev team)
│   ├── memory.py               # fact extraction, message scoring, history compression, uptime
│   ├── mentions.py             # rewrite <@id> as @username (display name, id) for the AI
│   ├── attachments.py          # download image attachments as base64 for the AI
│   ├── heartbeat.py            # optional Uptime Kuma / Pushgateway heartbeat
│   └── deploy.py               # register_commands(): global slash command sync (.up)
│
├── node-code/                  # Previous discord.js implementation (gitignored, do not touch)
└── python-code/                # Original py-cord implementation (gitignored, do not touch)
```

## Build/Run Commands

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt   # Install dependencies
.venv/bin/python main.py                    # Start the bot
start.bat                                   # Windows convenience launcher
```

No linting, testing, or build step configured. Manual testing via Discord. CI
(`.github/workflows/verify.yml`) byte-compiles everything and loads every extension on
Python 3.10, 3.11 and 3.13.

## Bot Configuration (main.py)

**Intents:** `guilds`, `guild_messages`, `members`, `message_content` (everything else off).

**Prefix:** `.` (defined in `config.py`)

**Bot class:** `LmpBot`, a `discord.Bot` subclass whose `start()` runs `init_storage()`
before connecting. It is a plain `discord.Bot`, not `commands.Bot`: prefix commands are
parsed by hand in `events/message_create.py`, after the dont_talk and chatbot checks.

**Module loading:** `main.py` loads every non-underscore module in `commands/` and
`events/` with `bot.load_extension()`. Each module defines a `commands.Cog` and a
`setup(bot)` that adds it.

**Command sync:** `auto_sync_commands` is off. `events/ready.py` bulk-syncs every command
globally once on startup, and `.up` does the same on demand (`utils/deploy.py`).

## Dependencies

| Package | Purpose |
|---------|---------|
| `py-cord` >=2.8.1,<3 | Core bot framework (needs Python 3.10+) |
| `aiohttp` | HTTP for OpenAI, Ollama, attachments, heartbeat, /welcome kill switch |
| `pymongo` >=4.13 | MongoDB, async API (`AsyncMongoClient`) |
| `asyncpg` | Neon Postgres tier (pooled URL, statement cache off) |
| `supabase` | Supabase fallback tier (async client) |
| `google-genai` | Gemini chatbot SDK |
| `python-dotenv` | Load `.env` into the environment |

OpenAI, Ollama and Turso are used over their HTTP APIs, with no client libraries.

## Code Style

- **Language:** Python 3.10+, `async`/`await` throughout
- **Indentation:** 4 spaces
- **Quotes:** Double quotes
- **File naming:** `snake_case.py`; slash command files are named after the command
- **Variables / functions:** `snake_case`
- **Constants:** `UPPER_SNAKE_CASE`
- **Classes / cogs:** `PascalCase`

## Command Structures

### Slash Command (`commands/`)
```python
import discord
from discord.ext import commands


class Example(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(name="example", description="What it does.")
    async def example(
        self,
        ctx: discord.ApplicationContext,
        option: discord.Option(str, description="Option description.", required=True),
    ):
        await ctx.respond(f"got: {option}", ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(Example(bot))
```

### Event listener (`events/`)
```python
import discord
from discord.ext import commands


class SomeEvent(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_some_event(self, *args):
        ...


def setup(bot: discord.Bot):
    bot.add_cog(SomeEvent(bot))
```

Never override `on_interaction` or `on_connect` on the bot itself: py-cord dispatches
commands and syncs from those. A `Cog.listener()` runs alongside them and is fine.

### Prefix command
Prefix commands live inside `events/message_create.py` as `elif cmd == "...":` branches
dispatched off the configured prefix. Owner-only commands gate on
`is_owner_cached(bot, message.author.id)`.

## Adding New Commands

1. **Slash command:** Create `commands/your_command.py` with a cog and `setup(bot)`.
2. **Event listener:** Create `events/your_event.py` with a cog and `setup(bot)`.
3. **Prefix command:** Add an `elif cmd == "yourcmd":` branch inside `events/message_create.py`.
4. Modules auto-load on bot startup via `load_dir()` in `main.py`.
5. Slash commands sync on startup; run `.up` in Discord (owner only) to re-sync without a restart.

## Important Notes

1. **No build step**: Python runs the source directly (`python main.py`).
2. **Pure py-cord**: No ForgeScript, no Node.js. All logic is Python.
3. **Never commit** `.env` or token files.
4. **Members intent**: Required for member iteration / role lookups; must be enabled in
   BOTH code AND the Discord Developer Portal. Message Content intent likewise.
5. **Stored values are strings.** Discord ids are stored as strings and come back as
   strings, so compare with `str(channel.id) == stored`, and turn them back into ints
   (`utils.birthdays.snowflake()`) before `guild.get_role()` / `get_channel()`. Booleans are
   stored as `"true"`/`"false"` (the db helpers convert Python `bool` for you).
6. **Owner IDs**: Resolved at startup by `utils/owner.py` from `bot.application_info()`
   (every team member, or the single owner) and cached on `bot.owner_ids`. Owner-only
   slash commands gate on `await is_bot_owner(bot, user_id)`, which re-resolves if that
   cache is empty.
7. **Database compatibility**: table, collection and field names are the ones the
   previous Node.js version used (Mongo collections `guildvars`, `membervars`,
   `userfacts`, `chatmemories` with camelCase fields; SQL tables `guild_vars`,
   `member_vars`, `user_facts`, `chat_memory`, also used by Turso; timestamps written as JavaScript-style ISO
   strings). Don't rename them, or existing data disappears.
8. **Legacy code**: `node-code/` (the discord.js version) and `python-code/` (the original
   py-cord version) are kept locally for reference and are gitignored. Do not modify them;
   the Python code at the repo root is the source of truth.
