# AGENTS.md - Codebase Guidelines for AI Agents

## Project Overview

This is **lmpbot-beta**, a Discord bot built with [discord.js](https://discord.js.org) (v14+).
The bot uses `mongoose` (MongoDB) for persistence, the `@google/generative-ai` SDK for the
Gemini chatbot, and supports both prefix commands (`.`) and slash commands.

## File Structure

```
lmpbot-beta/
├── index.js                    # Entry point — Client setup, intents, command/event loaders, mongo connect
├── config.js                   # Env/config loader (reads .env via dotenv)
├── package.json                # Node dependencies + scripts
├── start.bat                   # Windows launcher (pnpm install && pnpm start)
├── setup-lmpbot.sh             # Raspberry Pi / Linux installer (systemd + auto-updater)
├── .env                        # Bot token, Gemini key, Mongo URI
│                               # (DANGER_DONTSHARETOYKEN, GEMINI_API_KEY, MONGODB_URI)
│
├── commands/                   # Slash commands (auto-loaded; one command per file)
│   ├── help.js                 # /help
│   ├── members.js              # /members - show verified members
│   ├── welcome.js              # /welcome - mass welcome sender
│   ├── set_chatbot_channel.js  # /set_chatbot_channel
│   ├── set_bot_channel.js      # /set_bot_channel
│   ├── set_forum_channel.js    # /set_forum_channel
│   ├── set_news_channel.js     # /set_news_channel
│   └── set_verification_role.js# /set_verification_role
│
├── events/                     # discord.js event handlers (auto-loaded)
│   ├── ready.js                # ClientReady - startup log, owner resolution, status loop
│   ├── messageCreate.js        # prefix commands, dont_talk auto-ban, chatbot replies
│   ├── interactionCreate.js    # slash command routing + button handling
│   ├── guildCreate.js          # guild join log
│   └── threadCreate.js         # Forum channel: auto-add staff to new threads
│
├── utils/
│   ├── db.js                   # mongoose models + guild/member/fact/chat helpers
│   ├── gemini.js               # Gemini chat helper (@google/generative-ai)
│   ├── memory.js               # fact extraction, message scoring, history compression, uptime
│   └── deploy.js               # registerCommands() — global slash command sync (.up)
│
└── python-code/                # Legacy py-cord implementation (gitignored, do not touch)
```

## Build/Run Commands

```bash
pnpm install         # Install dependencies
pnpm start           # Start the bot (node index.js)
pnpm dev             # Start with auto-reload (node --watch index.js)
start.bat            # Windows convenience launcher
```

No linting, testing, or build step configured. Manual testing via Discord.

## Bot Configuration (index.js)

**Intents:**
`Guilds`, `GuildMessages`, `GuildMembers`, `MessageContent`.

**Prefix:** `.` (defined in `config.js`)

**Module loading:**
`index.js` reads every `.js` file in `commands/` and `events/`:
- `commands/` modules must `export default { data, execute }` (a `SlashCommandBuilder` + handler)
- `events/` modules must `export default { name, once?, execute }` (a discord.js event name + handler)
- Event handlers receive the normal event args plus `client` as the final argument.

## Dependencies

| Package | Purpose |
|---------|---------|
| `discord.js` >=14 | Core bot framework |
| `mongoose` >=8 | MongoDB ODM for guild/member/fact/chat state |
| `@google/generative-ai` | Gemini chatbot SDK |
| `dotenv` | Load `.env` into `process.env` |

## Code Style

- **Language:** Modern JavaScript (ESM, `"type": "module"`)
- **Indentation:** 2 spaces
- **Quotes:** Double quotes
- **File naming:** `camelCase.js` for events, `snake_case.js` for slash command files (name matches the command)
- **Variables / functions:** `camelCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Classes / models:** `PascalCase`

## Command Structures

### Slash Command (`commands/`)
```js
import { SlashCommandBuilder, MessageFlags } from "discord.js";

export default {
  data: new SlashCommandBuilder()
    .setName("example")
    .setDescription("What it does.")
    .addStringOption((o) => o.setName("option").setDescription("Option description.").setRequired(true)),

  async execute(interaction) {
    const option = interaction.options.getString("option");
    await interaction.reply({ content: `got: ${option}`, flags: MessageFlags.Ephemeral });
  },
};
```

### Event handler (`events/`)
```js
import { Events } from "discord.js";

export default {
  name: Events.SomeEvent,
  // once: true,   // optional
  async execute(/* ...args, client */) {
    // ...
  },
};
```

### Prefix command
Prefix commands live inside `events/messageCreate.js` as `else if (cmd === "...")` branches
dispatched off the configured prefix. Owner-only commands gate on
`message.client.ownerIds.has(message.author.id)`.

## Adding New Commands

1. **Slash command:** Create `commands/your_command.js` with a default `{ data, execute }` export.
2. **Event handler:** Create `events/yourEvent.js` with a default `{ name, execute }` export.
3. **Prefix command:** Add an `else if (cmd === "yourcmd")` branch inside `events/messageCreate.js`.
4. Modules auto-load on bot startup via the loaders in `index.js`.
5. After adding/changing slash commands, run `.up` in Discord (owner only) to sync them globally.

## Important Notes

1. **No build step** — Node runs the source directly (`node index.js`).
2. **Pure discord.js** — No ForgeScript, no Python. All logic is JavaScript.
3. **Never commit** `.env` or token files.
4. **Members intent** — Required for member iteration / role lookups; must be enabled in
   BOTH code AND the Discord Developer Portal.
5. **Slash command registration** — `.up` calls `client.application.commands.set(...)` (see `utils/deploy.js`).
6. **Owner IDs** — Resolved at startup in `events/ready.js` from `client.application` (team members or single owner).
7. **Database** — MongoDB via `mongoose`; connection string comes from `MONGODB_URI`. Collections/indexes
   are created lazily by the models in `utils/db.js`. Discord snowflakes are stored as strings.
8. **Legacy code** — The original py-cord implementation is preserved under `python-code/` and is
   gitignored. Do not modify it; the Node.js version at the repo root is the source of truth.
```
