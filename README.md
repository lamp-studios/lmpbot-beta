# lmpbot-beta

A Discord bot built with [ForgeScript](https://docs.botforge.org) featuring moderation, verification, and server management tools.

## Features

- **Verification system** - Role-based member verification
- **Welcome messages** - Mass welcome message sender with mention control
- **Anti-bot detection** - Auto-timeout for messages in restricted channels
- **Server management** - Game server creation via Pterodactyl panel
- **Slash & prefix commands** - Full support for both command types

## Setup

### Prerequisites

- [Node.js](https://nodejs.org/) v18+
- A [Discord bot application](https://discord.com/developers/applications) with the following privileged intents enabled:
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

## Commands

### Slash Commands

| Command | Permission | Description |
|---------|-----------|-------------|
| `/help` | Everyone | Shows all available commands |
| `/welcome` | Admin | Sends welcome messages for all members to a channel |
| `/members` | Everyone | Shows all verified members |
| `/set_verification_role` | Owner | Sets the role granted on verification |
| `/set_bot_channel` | Owner | Sets a channel for bot detection |
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
- [ForgeDB](https://github.com/tryforge/forge.db) - SQLite database extension
- [ForgeCanvas](https://github.com/tryforge/forge.canvas) - Image generation

## License

All rights reserved.
