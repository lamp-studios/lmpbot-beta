# lmpbot-beta

A Discord bot built with [Discord.JS](https://discord.js.org)
featuring moderation, verification, Gemini-powered chat, and server management tools.

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

- [NodeJS](https://nodejs.org) v24+
- A [Discord bot application](https://discord.com/developers/applications) with the following privileged intents enabled:
  - Server Members Intent
  - Message Content Intent

### Installation

```bash
git clone https://github.com/lamp-studios/lmpbot-beta.git
cd lmpbot-beta
pnpm install
```

### Configuration

Create a `.env` file in the project root:

```env
# Required
DANGER_DONTSHARETOYKEN=your_discord_bot_token

# Optional — chatbot is disabled without it
GEMINI_API_KEY=your_gemini_api_key

# Storage (see "Database Setup" below). All three are optional; the bot falls
# back Mongo -> Supabase -> local SQLite, so with none set it still runs on SQLite.
MONGODB_URI=your_mongodb_connection_string
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_role_key
```

### Running

```bash
node index.js
```

On Windows you can also just double-click `start.bat`.

After the bot is online, run `.up` in Discord (owner only) to register slash commands.

### Raspberry Pi / Linux Auto-Deploy

A setup script is included for Raspberry Pi or any Linux server with systemd:

```bash
chmod +x setup-lmpbot.sh && sudo ./setup-lmpbot.sh
```

This will:
- Install Node.js and enable pnpm (via corepack)
- Clone the repo and install dependencies with `pnpm install`
- Prompt for your bot token and create `.env` (bot token, Gemini key, Mongo URI)
- Set up a systemd service (auto-start on boot)
- Set up an auto-updater that checks for new commits every 5 minutes

## Database Setup

The bot uses a **tiered storage fallback**. Every read/write is attempted in
priority order and falls through to the next backend on failure (e.g. MongoDB
running out of storage, or Supabase erroring):

```
MongoDB  ->  Supabase  ->  SQLite (local file)
```

You can configure **any subset** of these:

- Set **none** and the bot runs entirely on a local SQLite file — zero setup,
  fine for testing or a single small server.
- Set **MongoDB** as your primary, and optionally add **Supabase** as a safety
  net for when the Mongo free tier fills up.
- SQLite is **always** the last-resort fallback, so your data is never lost even
  if the remote databases are down.

> **Note:** the SQLite fallback uses Node's built-in `node:sqlite`, which
> requires **Node ≥ 22.5** (the recommended v24+ covers this).

### MongoDB (primary)

Using a free [MongoDB Atlas](https://www.mongodb.com/atlas) cluster:

1. Create an account and a **free (M0) cluster**.
2. **Database Access** → *Add New Database User* → create a user with a username
   and password (give it *Read and write to any database*).
3. **Network Access** → *Add IP Address* → allow your server's IP, or
   `0.0.0.0/0` to allow anywhere (simplest for a Raspberry Pi on a dynamic IP).
4. **Connect** → *Drivers* → copy the connection string. It looks like:
   ```
   mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/lmpbot?retryWrites=true&w=majority
   ```
5. Replace `<user>`/`<password>`, add a database name (e.g. `/lmpbot`), and put
   it in `.env` as `MONGODB_URI`.

Collections and indexes are created automatically on first write — no manual
schema step needed.

### Supabase (fallback)

Using a free [Supabase](https://supabase.com) project:

1. Create a project and wait for it to finish provisioning.
2. Open the **SQL Editor**, paste the contents of
   [`supabase-schema.sql`](supabase-schema.sql), and run it once. This creates
   the `guild_vars`, `member_vars`, `user_facts`, and `chat_memory` tables.
3. **Project Settings → API**:
   - Copy the **Project URL** → `.env` as `SUPABASE_URL`.
   - Copy the **`service_role` key** (not the `anon` key) → `.env` as
     `SUPABASE_KEY`. The service-role key is required so the bot can write past
     Row Level Security.

> ⚠️ The `service_role` key bypasses RLS — treat it like a password and never
> commit it or expose it client-side.

If `SUPABASE_URL`/`SUPABASE_KEY` are unset, the Supabase tier is simply skipped.

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
| `.exe` | Owner | Evaluates JavaScript code |
| `.send_new` | Owner | Broadcasts a message to every guild's news channel |
| `.ping` | Everyone | Ping the bot |
| `.info` | Everyone | Show bot info (ping, OS, etc.) |
| `.verify` | Everyone | Verify yourself on the server |

## Tech Stack

- [discord.js](https://discord.js.org) - Discord bot framework
- [mongoose](https://mongoosejs.com) - MongoDB ODM (primary storage)
- [@supabase/supabase-js](https://github.com/supabase/supabase-js) - Supabase client (fallback storage)
- [node:sqlite](https://nodejs.org/api/sqlite.html) - built-in SQLite (last-resort local storage)
- [@google/generative-ai](https://www.npmjs.com/package/@google/generative-ai) - Gemini chatbot SDK
- [dotenv](https://github.com/motdotla/dotenv) - Environment variable loading

## License

All rights reserved.
