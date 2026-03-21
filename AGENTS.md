# AGENTS.md - Codebase Guidelines for AI Agents

## Project Overview

This is **lmp-bot-beta**, a Discord bot built with ForgeScript (`@tryforge/forgescript` v2.6.0).
The bot uses ForgeDB for persistence, ForgeCanvas for image generation, and supports both prefix commands (`.`) and slash commands.

## File Structure

```
lmpbot-beta/
├── index.js                    # Entry point — ForgeClient setup, intents, events, extensions
├── package.json                # Dependencies and scripts
├── forgeconfig.json            # ForgeLSP config
├── .env                        # Bot token (DANGER_DONTSHARETOYKEN)
├── server_scraper.js           # Standalone Discord server invite scraper (separate tool)
│
├── cmds/                       # Prefix commands (`.` prefix, messageCreate)
│   ├── channel.js              # Anti-bot channel detection
│   ├── exe.js                  # Owner-only eval command (.exe)
│   ├── ping.js                 # Ping command
│   ├── ready.js                # clientReady event (logs "Successfully loaded")
│   ├── up.js                   # Owner-only slash command registration
│   ├── verify.js               # User verification command
│   ├── checkglobal.old         # Archived command
│   └── list.old                # Archived command
│
├── slash/                      # Slash commands (application commands)
│   ├── welcome.js              # Mass welcome message sender
│   ├── help.js                 # Help command (uses container/text display components)
│   ├── members.js              # Show verified members list
│   ├── createserver.js         # Create game server via API
│   ├── set_verify_role.js      # Set verification role (owner only)
│   ├── set_dont_talk_channel.js # Set anti-bot channel (owner only)
│   ├── find_tags.old           # Archived command
│   └── test.old                # Archived command
│
├── routes/                     # API route handlers (currently unused, Quoriel API commented out)
│   ├── createserver.js
│   └── createuser.js
│
├── database/
│   └── forge.db                # SQLite database (ForgeDB)
│
├── discord_token.txt           # Legacy token file
├── discord_token.txt.example   # Token file template
├── proxies.txt.example         # Proxy list template (for scraper)
├── tags.txt                    # Tags data file
├── invites.json                # Scraped invite data
├── invites.csv                 # Scraped invite data (CSV)
├── invites_detailed.json       # Detailed invite data
└── lmpbot-beta.zip             # Project archive
```

## Build/Run Commands

```bash
npm start       # Start the bot (node index.js)
npm run scrape  # Run the server scraper (node server_scraper.js)
```

No linting, testing, or build step configured. Manual testing via Discord.

## Bot Configuration (index.js)

**Intents:**
Guilds, GuildMembers, GuildModeration, GuildInvites, GuildMessages, GuildMessageReactions,
DirectMessages, DirectMessageReactions, DirectMessageTyping, AutoModerationConfiguration,
AutoModerationExecution, GuildMessagePolls, DirectMessagePolls, MessageContent

**Extensions:**
- ForgeDB (SQLite-backed persistence)
- ForgeCanvas (image generation)
- Quoriel API (commented out — game server panel integration)

**Prefix:** `.`

**Events:** autoMod, channel, emoji, guild, interaction, invite, message, role events

## Dependencies

| Package | Purpose |
|---------|---------|
| `@tryforge/forgescript` ^2.6.0 | Core bot framework (ForgeScript DSL) |
| `@tryforge/forge.db` ^2.1.0 | Database extension (SQLite) |
| `@tryforge/forge.canvas` ^1.2.2 | Canvas/image extension |
| `sqlite3` ^5.1.7 | SQLite driver |
| `@dotenvx/dotenvx` ^1.51.1 | Environment variable loading |
| `@quoriel/api` ^1.5.2 | Game panel API (currently unused) |
| `@quoriel/pterodactyl` | Pterodactyl panel client (currently unused) |
| `uWebSockets.js` v20.55.0 | WebSocket server (currently unused) |
| `https-proxy-agent` ^7.0.2 | Optional proxy support for scraper |

## Code Style

- **Module system:** CommonJS (`require`/`module.exports`)
- **Indentation:** 4 spaces preferred
- **Quotes:** Double quotes
- **Semicolons:** Always
- **File naming:** `snake_case.js`
- **Variables:** `camelCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Classes:** `PascalCase`
- **ForgeScript code:** Template literals in `code` property

## Command Structures

### Prefix Command (`cmds/`)
```javascript
module.exports = {
    type: "messageCreate",  // or "clientReady" for events
    name: "commandname",
    code: `ForgeScript code here`
};
```

### Slash Command (`slash/`)
```javascript
module.exports = {
    code: `ForgeScript code here`,
    data: {
        name: "command_name",
        description: "What the command does",
        default_member_permissions: 8, // Optional: Admin only
        options: [
            {
                name: "option_name",
                description: "Option description",
                type: 3, // STRING=3, INTEGER=4, BOOLEAN=5, USER=6, CHANNEL=7, ROLE=8
                required: true
            }
        ]
    }
};
```

## Adding New Commands

1. **Prefix command:** Create `cmds/yourcommand.js`
2. **Slash command:** Create `slash/your_command.js`
3. Commands auto-load on bot startup
4. After adding slash commands, run `.up` in Discord (owner only) to register them

## Important Notes

1. **No build step** — JavaScript runs directly with Node.js
2. **ForgeScript DSL** — Commands use ForgeScript, not raw discord.js
3. **Never commit** `.env` or `discord_token.txt`
4. **GuildMembers intent** — Required for `$fetchMembers`/`$guildMemberIDs`; must be enabled in BOTH code AND Discord Developer Portal
5. **Slash command registration** — Use `.up` command to update Discord's command registry
6. **Owner ID:** `1056952213056004118`
