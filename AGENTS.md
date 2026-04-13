# AGENTS.md - Codebase Guidelines for AI Agents

## Project Overview

This is **lmp-bot-beta**, a Discord bot built with [discord.py](https://discordpy.readthedocs.io) (v2.4+).
The bot uses `aiosqlite` for persistence, `aiohttp` for HTTP calls (including Gemini web scraping),
and supports both prefix commands (`.`) and slash commands (`app_commands`).

## File Structure

```
lmpbot-beta/
├── main.py                     # Entry point — Client setup, intents, module loading
├── config.py                   # Env/config loader (Config class)
├── requirements.txt            # Python dependencies
├── start.bat                   # Windows launcher (python main.py)
├── setup-lmpbot.sh             # Raspberry Pi / Linux installer (systemd + auto-updater)
├── .env                        # Bot token + Gemini key (DANGER_DONTSHARETOYKEN, GEMINI_API_KEY)
│
├── commands/                   # Slash commands (auto-loaded app_commands)
│   ├── __init__.py
│   ├── help.py                 # /help
│   ├── members.py              # /members - show verified members
│   ├── welcome.py              # /welcome - mass welcome sender
│   └── settings.py             # /set_chatbot_channel, /set_bot_channel,
│                               # /set_forum_channel, /set_news_channel,
│                               # /set_verification_role
│
├── events/                     # discord.py event handlers (auto-loaded)
│   ├── __init__.py
│   ├── on_ready.py             # on_ready - startup log
│   ├── on_message.py           # prefix commands, dont_talk auto-ban, chatbot replies
│   ├── on_interaction.py       # interaction logging / routing
│   ├── on_guild_join.py        # on_guild_join handler
│   └── on_thread_create.py     # Forum channel: auto-add staff to new threads
│
├── utils/
│   ├── __init__.py
│   ├── db.py                   # aiosqlite helpers: guild/member var get/set/delete/search
│   └── gemini.py               # Gemini web-scraping chat helper
│
├── database/
│   └── forge.db                # SQLite database (created by utils/db.init_db)
│
├── invites.json                # Scraped invite data (legacy)
├── invites.csv                 # Scraped invite data (legacy CSV)
├── invites_detailed.json       # Detailed invite data (legacy)
└── lmpbot-beta.zip             # Project archive
```

## Build/Run Commands

```bash
python main.py       # Start the bot
start.bat            # Windows convenience launcher
```

No linting, testing, or build step configured. Manual testing via Discord.

## Bot Configuration (main.py)

**Intents:**
Defaults + `message_content` + `members`.

**Prefix:** `.` (defined in `config.py`)

**Module loading:**
`main.py` walks `commands/` and `events/` packages and calls each module's `setup(target)`:
- `commands/` modules receive the `CommandTree`
- `events/` modules receive the `Client`

## Dependencies

| Package | Purpose |
|---------|---------|
| `discord.py` >=2.4,<3 | Core bot framework |
| `aiosqlite` >=0.20 | Async SQLite driver for guild/member state |
| `aiohttp` >=3.9 | HTTP client (Gemini scraping, generic requests) |
| `python-dotenv` >=1.0 | Load `.env` into environment |

## Code Style

- **Language:** Python 3.10+ (uses `X | None` union syntax)
- **Indentation:** 4 spaces
- **Quotes:** Double quotes
- **File naming:** `snake_case.py`
- **Variables / functions:** `snake_case`
- **Constants:** `UPPER_SNAKE_CASE`
- **Classes:** `PascalCase`

## Command Structures

### Slash Command (`commands/`)
```python
import discord
from discord import app_commands


@app_commands.command(name="example", description="What it does.")
@app_commands.default_permissions(administrator=True)   # optional
@app_commands.describe(option="Option description.")
async def example_cmd(interaction: discord.Interaction, option: str):
    await interaction.response.send_message(f"got: {option}", ephemeral=True)


def setup(tree: app_commands.CommandTree):
    tree.add_command(example_cmd)
```

### Event handler (`events/`)
```python
import discord


def setup(client: discord.Client):
    @client.event
    async def on_something(...):
        ...
```

### Prefix command
Prefix commands live inside `events/on_message.py` as `elif cmd == "...":` branches
dispatched off the configured prefix. Owner-only commands gate on
`message.author.id in client.owner_ids`.

## Adding New Commands

1. **Slash command:** Create `commands/your_command.py` exposing a `setup(tree)` function.
2. **Event handler:** Create `events/on_your_event.py` exposing a `setup(client)` function.
3. **Prefix command:** Add an `elif cmd == "yourcmd":` branch inside `events/on_message.py`.
4. Modules auto-load on bot startup via `Client.load_modules` in `main.py`.
5. After adding/changing slash commands, run `.up` in Discord (owner only) to sync the tree.

## Important Notes

1. **No build step** — Python runs directly (`python main.py`).
2. **Pure discord.py** — No ForgeScript, no Node.js. All logic is Python.
3. **Never commit** `.env` or token files.
4. **Members intent** — Required for member iteration / role lookups; must be enabled in
   BOTH code AND the Discord Developer Portal.
5. **Slash command registration** — `.up` calls `client.tree.sync()`.
6. **Owner IDs** — Resolved at startup from `application_info()` (team members or single owner).
7. **Database** — `utils/db.init_db()` runs in `setup_hook`; tables are created on first boot
   at `database/forge.db`.
