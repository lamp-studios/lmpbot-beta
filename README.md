# lmpbot-beta

A Discord bot built with [Discord.JS](https://discord.js.org)
featuring moderation, verification, Gemini-powered chat, and server management tools.

## Features

- **Verification system** - Role-based member verification
- **Birthdays** - Daily announcements, an auto-granted birthday role and a custom message
- **Welcome messages** - Mass welcome message sender with mention control (currently disabled)
- **Anti-bot detection** - Auto-ban for messages posted in restricted channels
- **Gemini chatbot** - Reply to messages in a designated channel using Gemini, with per-user chat memory and remembered facts
- **Forum auto-staff** - Automatically add the server owner and a staff role to newly-created forum threads
- **News broadcast** - Push announcements to every guild's configured news channel
- **Uptime heartbeat** - Optional Uptime Kuma push and Prometheus Pushgateway metrics
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

# Optional, the chatbot is disabled without it
GEMINI_API_KEY=your_gemini_api_key

# Storage (see "Database Setup" below). All three are optional; the bot falls
# back Mongo -> Supabase -> local SQLite, so with none set it still runs on SQLite.
MONGODB_URI=your_mongodb_connection_string
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_role_key

# Optional monitoring (see "Monitoring" below). Both are skipped if unset.
KUMA_PUSH_URL=your_uptime_kuma_push_url
PUSHGATEWAY_URL=your_prometheus_pushgateway_url
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

- Set **none** and the bot runs entirely on a local SQLite file, zero setup,
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

Collections and indexes are created automatically on first write, so there is no
manual schema step needed.

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

> ⚠️ The `service_role` key bypasses RLS, so treat it like a password and never
> commit it or expose it client-side.

If `SUPABASE_URL`/`SUPABASE_KEY` are unset, the Supabase tier is simply skipped.

## Commands

### Slash Commands

| Command | Permission | Description |
|---------|-----------|-------------|
| `/help` | Everyone | Shows all available commands |
| `/birthday set` | Everyone | Sets your own birthday as day/month, e.g. `30/01` |
| `/birthday list` | Everyone | Lists every birthday on the server in calendar order |
| `/birthday upcoming` | Everyone | Lists the birthdays in the next `days` days (default 30) |
| `/birthday visibility` | Everyone | Picks whether your `/birthday` replies are private or public |
| `/birthday settings` | Admin | Views or changes the birthday role, channel, message, ping and set-channel |
| `/birthday enable` | Admin | Turns the birthday feature on |
| `/birthday disable` | Admin | Turns the birthday feature off |
| `/welcome` | Owner | Sends welcome messages for all members to a channel (currently disabled) |
| `/members` | Everyone | Shows all verified members (ephemeral reply, mentions are not pinged) |
| `/set_verification_role` | Admin | Sets the role granted on verification, and enables verification. Run it with no role to remove the role and disable verification again |
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

## Birthdays

Members save a birthday with `/birthday set 30/01` (day/month, `30/1` and `3/1`
also parse). Admins configure the rest with `/birthday settings`:

| Option | What it does |
|--------|--------------|
| `role` | Role granted to a member for the day |
| `channel` | Channel the announcement is posted in |
| `message` | Custom announcement, supports `{user}`, `{mention}` and `{name}` |
| `ping_role` | Role pinged in the announcement (setting it also turns the ping on) |
| `ping` | Turns the announcement ping on or off |
| `set_channel` | Restricts `/birthday set` to one channel |

Running `/birthday settings` with no options prints the current configuration.
The feature stays off until an admin runs `/birthday enable`.

### Browsing birthdays

`/birthday list` prints every birthday on the server in calendar order, grouped
by month. `/birthday upcoming` prints only the ones that are close, soonest
first, over the next 30 days unless a `days` option says otherwise. Both skip
members who have left, never ping anyone, and cut off with a "…and N more" note
rather than overflowing Discord's message limit.

### Reply visibility

`/birthday` replies are only visible to the person who ran the command. Anyone
who would rather have them posted in the channel can flip that for themselves
with `/birthday visibility mode:Everyone (public)`, and back with
`mode:Only me (ephemeral)`. The preference is per-member per-server, it covers
`set`, `list`, `upcoming`, `settings` and `enable`/`disable`, and running
`/birthday visibility` with no option reports the current choice. Errors and
permission denials ignore the preference and stay private.

How the scheduler behaves:

- Dates are stored as a bare `DD/MM` string with no timezone, and are compared
  against the bot host's local date. Whichever calendar day the host is on is
  the day everyone gets announced.
- The scan runs every 30 minutes but does nothing before 08:00 host-local time,
  and marks each guild as done for the day once it runs. That holds across
  restarts, so nobody gets announced twice.
- The birthday role is reconciled on every run: today's celebrants get it, and
  anyone else still holding it (yesterday's celebrants) has it removed.
- `29/02` is accepted as a date, but it only announces in leap years.

## Monitoring

If `KUMA_PUSH_URL` is set, the bot pushes an [Uptime Kuma](https://uptime.kuma.pet)
push heartbeat every 60 seconds with its gateway ping and ready state. Any query
string on the URL is stripped before the bot adds its own parameters.

If `PUSHGATEWAY_URL` is set, the same loop also posts `lmpbot_up` and
`lmpbot_ping_ms` gauges to a [Prometheus Pushgateway](https://github.com/prometheus/pushgateway)
under the job name `lmpbot`.

The two are independent, so you can enable either, both or neither. With neither
set the heartbeat loop never starts.

## Tech Stack

- [discord.js](https://discord.js.org) - Discord bot framework
- [mongoose](https://mongoosejs.com) - MongoDB ODM (primary storage)
- [@supabase/supabase-js](https://github.com/supabase/supabase-js) - Supabase client (fallback storage)
- [node:sqlite](https://nodejs.org/api/sqlite.html) - built-in SQLite (last-resort local storage)
- [@google/generative-ai](https://www.npmjs.com/package/@google/generative-ai) - Gemini chatbot SDK
- [dotenv](https://github.com/motdotla/dotenv) - Environment variable loading

## License

All rights reserved.
