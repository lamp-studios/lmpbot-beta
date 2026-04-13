# lmpbot-beta

A Discord bot built with [discord.py](https://discordpy.readthedocs.io) featuring moderation, verification, Gemini-powered chat, and server management tools.

## Features

- **Verification system** - Role-based member verification
- **Welcome messages** - Mass welcome message sender with mention control
- **Anti-bot detection** - Auto-ban for messages posted in restricted channels
- **Gemini chatbot** - Reply to messages in a designated channel using Gemini
- **Forum auto-staff** - Automatically add a staff role to newly-created forum threads
- **News broadcast** - Push announcements to every guild's configured news channel
- **Slash & prefix commands** - Full support for both command types

## Setup

### Prerequisites

- [Python](https://www.python.org/) 3.10+
- A [Discord bot application](https://discord.com/developers/applications) with the following privileged intents enabled:
  - Server Members Intent
  - Message Content Intent

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

### Running

```bash
python main.py
```

On Windows you can also just double-click `start.bat`.

After the bot is online, run `.up` in Discord (owner only) to register slash commands.

### Raspberry Pi / Linux Auto-Deploy

A setup script is included for Raspberry Pi or any Linux server with systemd:

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
| `/help` | Everyone | Shows all available commands |
| `/welcome` | Admin | Sends welcome messages for all members to a channel |
| `/members` | Everyone | Shows all verified members |
| `/set_verification_role` | Admin | Sets the role granted on verification |
| `/set_bot_channel` | Admin | Sets the "dont talk" channel (auto-ban on message) |
| `/set_chatbot_channel` | Admin | Sets a channel for Gemini chatbot replies |
| `/set_forum_channel` | Admin | Sets a forum channel + staff role for auto-add on new threads |
| `/set_news_channel` | Admin | Sets the channel where bot news broadcasts are posted |

### Prefix Commands (`.`)

| Command | Permission | Description |
|---------|-----------|-------------|
| `.up` | Owner | Registers/updates slash commands |
| `.exe` | Owner | Evaluates Python code |
| `.send_new` | Owner | Broadcasts a message to every guild's news channel |
| `.ping` | Everyone | Ping the bot |
| `.info` | Everyone | Show bot info (ping, OS, etc.) |
| `.verify` | Everyone | Verify yourself on the server |

## Tech Stack

- [discord.py](https://discordpy.readthedocs.io) - Discord bot framework
- [aiosqlite](https://github.com/omnilib/aiosqlite) - Async SQLite for guild/member storage
- [aiohttp](https://docs.aiohttp.org) - HTTP client (Gemini web scraping)
- [python-dotenv](https://github.com/theskumar/python-dotenv) - Environment variable loading

## License

All rights reserved.
