# LmpBot

A Discord bot built with [Pycord](https://pycord.dev)
featuring moderation, verification, AI chat (Gemini, OpenAI or a local Ollama model), and server management tools.

## Features

- **Verification system** - Role-based member verification
- **Birthdays** - Daily announcements, an auto-granted birthday role and a custom message
- **Welcome messages** - Mass welcome message sender with mention control (currently disabled)
- **Anti-bot detection** - Auto-ban for messages posted in restricted channels
- **Server lockdown** - Hide every channel from a role bar one, with an exact one-command undo
- **AI chatbot** - Reply to messages in a designated channel, with per-user chat memory and remembered facts. Reads posted images on vision-capable models, and resolves mentions to real usernames so it knows who is who. Runs on Gemini, OpenAI or a local Ollama model, set globally or per server by the bot owner with `/setchatbotai`
- **Forum auto-staff** - Automatically add the server owner and a staff role to newly-created forum threads
- **News broadcast** - Push announcements to every guild's configured news channel
- **Uptime heartbeat** - Optional Uptime Kuma push and Prometheus Pushgateway metrics
- **Slash & prefix commands** - Full support for both command types

## Setup

### Prerequisites

- [Python](https://www.python.org) 3.10+ (py-cord 2.8 does not run on anything older)
- A [Discord bot application](https://discord.com/developers/applications) with the following privileged intents enabled:
  - Server Members Intent
  - Message Content Intent

### Installation

```bash
git clone https://github.com/lamp-studios/lmpbot-beta.git
cd lmpbot-beta
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt    # Windows: .venv\Scripts\pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root (or copy [`.env.example`](.env.example)):

```env
# Required
DANGER_DONTSHARETOYKEN=your_discord_bot_token

# Optional, the Gemini chatbot is disabled without it
GEMINI_API_KEY=your_gemini_api_key

# Optional, only for the OpenAI chatbot. The base URL defaults to OpenAI itself
# and can point at any OpenAI-compatible endpoint.
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1

# Optional, only for the Ollama chatbot. Defaults to http://127.0.0.1:11434,
# so you only need this if Ollama runs somewhere else.
OLLAMA_HOST=http://127.0.0.1:11434

# Storage (see "Database Setup" below). All optional; the bot falls back
# Mongo -> Supabase -> Neon -> Turso -> local SQLite, so with none set it still runs on SQLite.
MONGODB_URI=your_mongodb_connection_string
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_role_key
DATABASE_URL=your_neon_pooled_connection_string
DATABASE_URL_UNPOOLED=your_neon_direct_connection_string
TURSO_DATABASE_URL=libsql://your-db-your-org.turso.io
TURSO_AUTH_TOKEN=your_turso_database_token

# Optional monitoring (see "Monitoring" below). Both are skipped if unset.
# A key left blank (KEY=) counts as unset everywhere.
KUMA_PUSH_URL=your_uptime_kuma_push_url
PUSHGATEWAY_URL=your_prometheus_pushgateway_url

# Optional dashboard HTTP API (see "Dashboard API" below). Off unless BOT_API_KEY is set.
BOT_API_KEY=a_long_random_secret
BOT_API_PORT=8080
```

### Running

```bash
.venv/bin/python main.py
```

On Windows you can also just double-click `start.bat`, which creates the venv
and installs the requirements on first run.

Slash commands are synced to Discord every time the bot starts. Run `.up` in
Discord (owner only) to force a re-sync without restarting.

### Raspberry Pi / Linux Auto-Deploy

A setup script is included for Raspberry Pi or any Linux server with systemd:

```bash
chmod +x setup-lmpbot.sh && sudo ./setup-lmpbot.sh
```

This will:
- Install Python 3 and `venv` (or a uv-managed Python 3.12 if the system one is older than 3.10)
- Clone the repo into `~/lmpbot-beta` and install `requirements.txt` into `~/lmpbot-beta/.venv`
- Prompt for your bot token and create `.env`, or add any missing keys to an existing one
- Set up a systemd service (auto-start on boot)
- Set up an auto-updater that checks for new commits every 5 minutes and reinstalls requirements

It is safe to re-run, and re-running it is also how an old Node.js install is
migrated: it stops the bot, swaps the code over, deletes `node_modules/` and
keeps `.env` and `database/` as they are. A 64-bit Raspberry Pi OS is
recommended, since some dependencies have no prebuilt 32-bit ARM wheels.

## Database Setup

The bot uses a **tiered storage fallback**. Every read/write is attempted in
priority order and falls through to the next backend on failure (e.g. MongoDB
running out of storage, or Supabase erroring):

```
MongoDB  ->  Supabase  ->  Neon  ->  Turso  ->  SQLite (local file)
```

You can configure **any subset** of these:

- Set **none** and the bot runs entirely on a local SQLite file, zero setup,
  fine for testing or a single small server.
- Set **MongoDB** as your primary, and optionally add **Supabase** as a safety
  net for when the Mongo free tier fills up.
- SQLite is **always** the last-resort fallback, so your data is never lost even
  if the remote databases are down.

> **Note:** the SQLite fallback uses Python's built-in `sqlite3` module and
> lives in `database/fallback.db`.

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

Collections and indexes are created automatically on first start, so there is no
manual schema step needed. The collection names (`guildvars`, `membervars`,
`userfacts`, `chatmemories`) are the ones the earlier Node.js version created, so
an existing database carries straight over. If the URI names no database, `test`
is used, again matching the earlier version.

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

### Neon (fallback)

Using a free [Neon](https://neon.com) project (Lakebase Postgres):

1. Create a project, then link this folder to it with the Neon CLI
   (`npm i -g neon`, `neon login`, `neon link`). That writes `DATABASE_URL` and
   `DATABASE_URL_UNPOOLED` into `.env`. Copying both connection strings from the
   dashboard's **Connect** dialog works too.
2. That's it: the tables are created on first start over the direct
   (`DATABASE_URL_UNPOOLED`) connection, and normal traffic goes through the pooled
   `DATABASE_URL`. The schema is the same as [`supabase-schema.sql`](supabase-schema.sql).

The bot uses [asyncpg](https://github.com/MagicStack/asyncpg) with its statement
cache off, as Neon's pooler (PgBouncer, transaction mode) requires. Idle Neon
computes suspend after a few minutes; the first query afterwards takes a moment
longer. If `DATABASE_URL` is unset, the Neon tier is skipped.

`neon.ts` and `package.json` are Neon's infrastructure config for `neon deploy`
(it only comes in TypeScript). It declares Postgres only, and the bot itself never
runs it.

### Turso (fallback)

Using a free [Turso](https://turso.tech) database (hosted libSQL, i.e. SQLite):

1. Create a database in the Turso dashboard, or with the CLI:
   `turso db create lmpbot`.
2. Copy its URL (`libsql://<db>-<org>.turso.io`) → `.env` as `TURSO_DATABASE_URL`.
3. Create a read/write token for it (`turso db tokens create lmpbot`) → `.env` as
   `TURSO_AUTH_TOKEN`.

The tables are created automatically on first start, with the same schema as the
local SQLite file. The bot talks to Turso over its HTTP API, so there is no extra
dependency to install. If either variable is unset, the Turso tier is skipped.

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
| `/lockdown` | Admin | Hides every channel from a `role` (default `@everyone`), apart from an optional `channel-exception` |
| `/undolockdown` | Admin | Lifts the lockdown and restores every channel's View Channel permission |
| `/welcome` | Owner | Sends welcome messages for all members to a channel (currently disabled) |
| `/members` | Everyone | Shows all verified members (ephemeral reply, mentions are not pinged) |
| `/set_verification_role` | Admin | Sets the role granted on verification, and enables verification. Run it with no role to remove the role and disable verification again |
| `/set_bot_channel` | Admin | Sets the "dont talk" channel (auto-ban on message) and an optional log channel. Run it with no options to turn both off |
| `/set_chatbot_channel` | Admin | Sets a channel for AI chatbot replies, including posted images |
| `/setchatbotai` | Owner | Picks the chatbot AI: `gemini`, `openai`, or `ollama` with a model name that is installed automatically. `scope` sets it for this server, globally for every server, or clears the server's own setting. Run it with no options to see the current one |
| `/delete_data` | Owner | Deletes a user's chat memory, remembered facts and member settings (birthday, verification) from every server and every database, after a Confirm / Cancel prompt. Takes a username, mention or user id |
| `/set_forum_channel` | Admin | Sets a forum channel + staff role for auto-add on new threads |
| `/set_news_channel` | Admin | Sets the channel where bot news broadcasts are posted |

### Prefix Commands (`.`)

| Command | Permission | Description |
|---------|-----------|-------------|
| `.up` | Owner | Registers/updates slash commands |
| `.exe` | Owner | Runs Python code (`bot`, `client`, `message`, `discord` in scope) |
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

## Lockdown

`/lockdown` denies **View Channel** in every channel on the server.
`/lockdown channel-exception:#announcements` leaves that one channel visible;
with no exception the whole server goes dark. `/undolockdown` puts it all back.

`role` picks who gets shut out and defaults to `@everyone`:

```
/lockdown channel-exception:#announcements
/lockdown channel-exception:#announcements role:@Members
```

Point it at your member role if that role is what grants View Channel. On a
server where access is gated behind a "verified" or "member" role, a deny on
`@everyone` changes nothing for the people who have it.

Running `/lockdown` again for a **different** role folds that role into the same
lockdown, and one `/undolockdown` lifts them all. A role that is already locked
is refused, because a second pass would save the locked-down permissions as the
ones to restore and there'd be nothing left to go back to.

What it does and does not touch:

- Only the target role's **View Channel** bit is changed. Every other overwrite,
  role and permission is left exactly as it is.
- Anyone whose *other* roles explicitly allow View Channel (staff, moderators)
  still sees everything. The lockdown only takes away the access that came from
  the role you named, which is what leaves your team a way back in.
- A role holding **Administrator** ignores channel permissions entirely, so
  locking one down hides nothing. The reply says so if you try.
- Channels the role **already couldn't see** are skipped, so lifting the
  lockdown can never reveal a private channel it never touched.
- Categories are locked too, and each channel is edited individually, because the API
  does not push category permissions down to the channels inside them.
- The exception channel is *explicitly* allowed rather than just skipped, so it
  is visible whatever it inherited before. If it was hidden beforehand, the reply
  says so.
- Threads are skipped; they follow their parent channel.

The state before the lockdown is written to the database per role and per channel
(allowed, denied or unset), which is what lets `/undolockdown` restore each
channel precisely instead of flattening everything to "visible". It survives a
restart, so an undo still works days later. A role deleted while the lockdown is
running is simply reported; Discord drops its overwrites along with it.

The bot needs **Manage Roles**. Channels it can't edit are skipped and named in
the reply. If it isn't an administrator *and* it holds the role being locked down
(which `@everyone` always is), it grants itself a temporary View Channel allow on
each channel it hides, otherwise the deny would apply to the bot too and lock it
out of undoing its own lockdown. Those temporary overwrites are removed by
`/undolockdown`. Anything that fails to restore stays on record, so running
`/undolockdown` again picks up only what is left.

## Monitoring

If `KUMA_PUSH_URL` is set, the bot pushes an [Uptime Kuma](https://uptime.kuma.pet)
push heartbeat every 60 seconds with its gateway ping and ready state. Any query
string on the URL is stripped before the bot adds its own parameters.

If `PUSHGATEWAY_URL` is set, the same loop also posts `lmpbot_up` and
`lmpbot_ping_ms` gauges to a [Prometheus Pushgateway](https://github.com/prometheus/pushgateway)
under the job name `lmpbot`.

The two are independent, so you can enable either, both or neither. With neither
set the heartbeat loop never starts.

## Dashboard API

The bot runs a small JSON HTTP API in its own process, so an external web
dashboard can ask about the bot's state. It answers from the bot's in-memory
cache and never calls Discord's REST API.

| Variable | Default | What it does |
|----------|---------|--------------|
| `BOT_API_KEY` | (unset) | Shared secret the dashboard sends. With no key the API does not start, and the bot runs as normal |
| `BOT_API_PORT` | `8080` | Preferred port. The server binds to `0.0.0.0` |

Generate a key with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`.

If the preferred port is taken, the server tries the next 19 ports up, then lets
the OS pick any free one. The port it ends up on is logged and written to
`database/api-port`, so a tunnel or reverse proxy can read it from there. If the
server still cannot start, the error is logged and the bot keeps running without it.

Every route except `GET /health` needs `Authorization: Bearer <BOT_API_KEY>`;
a missing or wrong key gets `401 {"error": "Unauthorized"}`. Request bodies are
capped at 64 KB, unknown routes return `404` and wrong methods `405`, all as
JSON. Neither the key nor request headers are ever logged.

| Route | Auth | Description |
|-------|------|-------------|
| `GET /health` | No | `{"ok": true, "ready": <bool>}`, where `ready` is whether the gateway connection is ready |
| `POST /guilds/check` | Yes | Body `{"guildIds": ["123...", ...]}` (at most 500 snowflake strings). Returns `{"guildIds": [...]}`, the ones the bot is in. `503` until the bot is ready |

```bash
curl -X POST https://bot.example.com/guilds/check \
  -H "Authorization: Bearer $BOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"guildIds": ["123456789012345678"]}'
```

> ⚠️ The API itself speaks plain HTTP. In production, expose it **only over
> HTTPS**, through a reverse proxy (Caddy, nginx) or a tunnel (Cloudflare Tunnel,
> Tailscale Funnel), and don't open the raw port to the internet, or the key
> travels in clear text.

Routes live in `api/routes/`, separate from the server setup in `api/server.py`.
To add one, put a handler in a module there and list its `routes` table in
`api/routes/__init__.py`. Routes require the key by default; only handlers
decorated with `@public` skip it.

## Tech Stack

- [Pycord](https://pycord.dev) - Discord bot framework (`py-cord`)
- [PyMongo](https://pymongo.readthedocs.io) - MongoDB driver, async API (primary storage)
- [supabase-py](https://github.com/supabase/supabase-py) - Supabase client (fallback storage)
- [asyncpg](https://github.com/MagicStack/asyncpg) - Postgres driver for the Neon tier
- [Turso](https://docs.turso.tech/sdk/http/reference) - hosted libSQL (fallback storage), over its HTTP API with aiohttp (no extra dependency)
- [sqlite3](https://docs.python.org/3/library/sqlite3.html) - built-in SQLite (last-resort local storage)
- [google-genai](https://pypi.org/project/google-genai/) - Gemini chatbot SDK
- [OpenAI](https://platform.openai.com/docs/api-reference/chat) - optional chatbot models, over the Chat Completions HTTP API with aiohttp (no extra dependency)
- [Ollama](https://ollama.com) - optional local chatbot models, over its HTTP API with aiohttp (no extra dependency)
- [python-dotenv](https://github.com/theskumar/python-dotenv) - Environment variable loading

## License

Licensed under the [Apache License 2.0](./LICENSE).