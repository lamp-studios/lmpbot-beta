# lmpbot-beta

**LmpBot** is a small but efficient Discord utility bot focused on features that
the big popular bots (Dyno, Carl-bot, Sapphire) mostly *don't* have yet - anti-spambot
auto-banning, forum auto-staffing, a `.verify` flow, mass welcome resends, and an
optional Gemini-powered chatbot with memory.

It's built with [Pycord](https://docs.pycord.dev) (a maintained discord.py fork -
the project was originally written in ForgeScript, then rewritten in Python), uses
SQLite for storage, and is run 24/7 on a Raspberry Pi.

Made by **Lamp Studios** ([@lampyt](https://github.com/lamp-studios)).

## Features

- **Anti-bot detection** - designate a "don't talk" channel; anyone who posts there
  is soft-banned (ban + immediate unban) to wipe their messages and kick them out.
- **`.verify` system** - role-based member verification that has to be explicitly
  enabled per-server by setting a verification role.
- **Welcome messages** - mass-resend a welcome message for every member into a chosen
  channel, with a toggle for whether members get pinged. *(Currently gated off by a
  remote kill-switch to comply with Top.gg's mass-mention rules.)*
- **Forum auto-staff** - when a thread is created in a configured forum channel, the
  bot automatically pulls in the guild owner and everyone with the staff role.
- **Gemini chatbot + memory** - point the bot at a channel and it replies using Google's
  `gemini-2.5-flash`. It keeps per-user conversation history and extracts long-term
  "facts" (name, what you're building, likes/dislikes) so replies stay contextual.
- **News broadcast** - push a single announcement to every server's configured news
  channel at once (owner only).
- **Slash & prefix commands** - both `/` application commands and `.` prefix commands.

## How the Gemini memory works

The chatbot doesn't just send the latest message - it builds a prioritized context
window for each user:

1. Every message (user + bot) is stored in a `chat_memory` table.
2. On each reply the last ~50 messages are pulled and scored - longer messages and
   ones containing keywords like *remember*, *important*, *my name is*, *project* score
   higher; throwaway messages (`lol`, `ok`, emoji) score lower.
3. Compression is gentle - even low-scoring messages keep a generous character budget,
   all kept under a ~20k char ceiling, then re-ordered chronologically.
4. The selected messages are formatted into a labelled transcript (each message on its
   own line, separated by a blank line) and sent to Gemini behind a header line that
   tells it this is the prior chat history.
5. Separately, simple regex extracts durable **user facts** (name, project, identity,
   likes, hates) into a `user_facts` table and prepends them to the context, so the bot
   "remembers" you across conversations.

## Setup

### Prerequisites

- [Python](https://www.python.org/) 3.10+
- A [Discord bot application](https://discord.com/developers/applications) with these
  privileged intents enabled:
  - Server Members Intent
  - Message Content Intent
- *(Optional)* a [Google AI Studio](https://aistudio.google.com/) API key for the
  Gemini chatbot.

### Installation

```bash
git clone https://github.com/lamp-studios/lmpbot-beta.git
cd lmpbot-beta
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
DANGER_DONTSHARETOYKEN=your_discord_bot_token
GEMINI_API_KEY=your_gemini_api_key
```

Only the token is strictly required - without `GEMINI_API_KEY` the chatbot channel
simply won't respond and everything else works fine.

### Running

```bash
python main.py
```

On Windows you can also just double-click `start.bat`.

After the bot is online, run `.up` in Discord (owner only) to register slash commands.

### Raspberry Pi / Linux Auto-Deploy

A setup script is included for a Raspberry Pi or any Linux server with systemd:

```bash
chmod +x setup-lmpbot.sh && sudo ./setup-lmpbot.sh
```

This will:
- Install Python 3 and build tools
- Clone the repo and create a virtualenv
- Install Python dependencies from `requirements.txt`
- Prompt for your bot token and create `.env`
- Set up a systemd service (auto-start on boot)
- Set up an auto-updater that checks for new commits every 5 minutes

## Commands

### Slash Commands

| Command | Permission | Description |
|---------|-----------|-------------|
| `/help` | Everyone | Shows available commands (still a bit incomplete) |
| `/members` | Everyone | Lists all verified members |
| `/welcome` | Owner | Mass-resends a welcome message for every member *(currently disabled)* |
| `/set_verification_role` | Admin | Sets the role granted on verification (enables `.verify`) |
| `/set_bot_channel` | Admin | Sets the "don't talk" channel (auto-soft-ban on message) |
| `/set_chatbot_channel` | Admin | Sets a channel for Gemini chatbot replies |
| `/set_forum_channel` | Admin | Sets a forum channel + staff role for auto-add on new threads |
| `/set_news_channel` | Admin | Sets the channel where bot news broadcasts are posted |

Passing the relevant command its option with no value (e.g. `/set_chatbot_channel`
with no channel) clears that setting.

### Prefix Commands (`.`)

| Command | Permission | Description |
|---------|-----------|-------------|
| `.ping` | Everyone | Pong + latency in ms |
| `.info` | Everyone | Bot info (ping, uptime, OS) |
| `.verify` | Everyone | Verify yourself (only if a verification role is set) |
| `.up` | Owner | Registers/updates slash commands |
| `.exe` | Owner | Evaluates Python code through the bot |
| `.send_new` | Owner | Broadcasts a message to every guild's news channel |

## Project Structure

```
main.py                  # entrypoint: builds the bot, auto-loads commands + events
config.py                # loads token / Gemini key / prefix from .env
commands/                # slash commands (auto-loaded; each exposes a setup(bot))
  help.py  members.py  settings.py  welcome.py
events/                  # gateway event handlers (auto-loaded the same way)
  on_message.py          #   prefix cmds, anti-bot, chatbot + memory
  on_interaction.py      #   slash dispatch + "learn more" button
  on_thread_create.py    #   forum auto-staff
  on_ready.py            #   presence/status loop
  on_guild_join.py
utils/
  db.py                  # aiosqlite helpers + schema (guild/member vars, facts, memory)
  gemini.py              # Generative Language API client
```

Commands and events are discovered automatically - any module under `commands/` or
`events/` that defines a `setup(bot)` function is loaded on startup, so adding a feature
is just dropping in a new file.

## Tech Stack

- [Pycord](https://docs.pycord.dev) - Discord bot framework (discord.py fork)
- [aiosqlite](https://github.com/omnilib/aiosqlite) - async SQLite for guild/member/memory storage
- [aiohttp](https://docs.aiohttp.org) - async HTTP client (Gemini API calls)
- [python-dotenv](https://github.com/theskumar/python-dotenv) - environment variable loading

## License

All rights reserved.
