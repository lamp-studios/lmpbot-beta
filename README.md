# lmpbot-beta

A Discord bot built with [ForgeScript](https://docs.botforge.org) featuring moderation, verification, and server management tools.

## Features

- **Verification system** - Role-based member verification
- **Welcome messages** - Mass welcome message sender with mention control
- **Anti-bot detection** - Auto-delete, timeout, strike, DM, and kick for messages in restricted "dont talk" channels
- **Server management** - Game server creation via Pterodactyl panel
- **Slash & prefix commands** - Full support for both command types

## Setup

### Prerequisites

- [Node.js](https://nodejs.org/) v22+
- A [Discord bot application](https://discord.com/developers/applications) with the following privileged intents enabled:
  - Presence Intent
  - Server Members Intent
  - Message Content Intent

### Installation

```bash
git clone https://github.com/lamp-studios/lmpbot-beta.git
cd lmpbot-beta
npm install
```

### Configuration

1. Copy `.env.example` or create a `.env` file:
```env
DANGER_DONTSHARETOYKEN=your_discord_bot_token
```

2. (Optional) For the server scraper, copy `discord_token.txt.example` to `discord_token.txt` and add your token.

### Running

```bash
npm start
```

After the bot is online, run `.up` in Discord to register slash commands.

### Raspberry Pi / Linux Auto-Deploy

A setup script is included for Raspberry Pi or any Linux server with systemd:

```bash
chmod +x setup-lmpbot.sh && sudo ./setup-lmpbot.sh
```

This will:
- Install Node.js v22 and build tools
- Clone the repo and install dependencies
- Rebuild native modules (sqlite3) for ARM
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
| `/set_bot_channel` | Admin | Sets a channel for bot detection (auto-kick/timeout on message) |
| `/createserver` | Admin | Creates a game server on the panel |

### Prefix Commands (`.`)

| Command | Permission | Description |
|---------|-----------|-------------|
| `.up` | Owner | Registers/updates slash commands |
| `.exe` | Owner | Evaluates ForgeScript code |
| `.ping` | Everyone | Ping the bot |
| `.verify` | Everyone | Verify yourself on the server |

## Tech Stack

- [ForgeScript](https://docs.botforge.org) - Discord bot framework
- [ForgeDB](https://github.com/tryforge/ForgeDB) - SQLite database extension
- [ForgeCanvas](https://github.com/tryforge/forgecanvas) - Image generation

## License

All rights reserved.
