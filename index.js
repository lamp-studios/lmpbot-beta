const { ForgeClient } = require("@tryforge/forgescript");
const { ForgeDB } = require("@tryforge/forge.db");
const { ForgeCanvas } = require("@tryforge/forge.canvas");
const { ForgeColor } = require("forge.color");
const { QuorielApi } = require("@quoriel/api");
require('@dotenvx/dotenvx').config()

const db = new ForgeDB({
    events: [
            "connect",
            "variableCreate",
            "variableDelete",
            "variableUpdate"
        ]
});

const client = new ForgeClient({
    intents: [
        "Guilds",
        "GuildMembers",
        "GuildModeration",
        "GuildInvites",
        "GuildMessages",
        "GuildMessageReactions",
        "DirectMessages",
        "DirectMessageReactions",
        "DirectMessageTyping",
        "AutoModerationConfiguration",
        "AutoModerationExecution",
        "GuildMessagePolls",
        "DirectMessagePolls",
        "MessageContent"
    ],
    events: [
        "autoModerationActionExecution",
        "autoModerationRuleCreate",
        "autoModerationRuleDelete",
        "autoModerationRuleUpdate",
        "channelCreate",
        "channelDelete",
        "channelPinsUpdate",
        "channelUpdate",
        "clientReady",
        "emojiCreate",
        "emojiDelete",
        "emojiUpdate",
        "error",
        "guildCreate",
        "guildUpdate",
        "interactionCreate",
        "inviteCreate",
        "inviteDelete",
        "messageCreate",
        "messageDelete",
        "messagePollVoteAdd",
        "messagePollVoteRemove",
        "messageReactionAdd",
        "messageReactionRemove",
        "messageReactionRemoveAll",
        "messageReactionRemoveEmoji",
        "messageUpdate",
        "roleCreate",
        "roleDelete",
        "roleUpdate",
        "threadCreate"
    ],
    extensions: [
        db,
        new ForgeCanvas(),
        new ForgeColor()
	//new QuorielApi({
    		//port: 3000,
    		//path: "routes",
	//}),
    ],
    prefixes: ["."]
});

client.commands.load('./cmds');
client.applicationCommands.load('./slash');

// Add this to your index.js file after creating the client

client.functions.add({
    name: "readLargeFile",
    params: ["filepath"],
    code: `
    $return[$djsEval[const fs = require('fs'); const path = require('path'); let result = ''; try { const fullPath = path.resolve('$env[filepath]'); if (fs.existsSync(fullPath)) { result = fs.readFileSync(fullPath, 'utf-8'); } } catch (error) { console.error('Error reading file:', error); } result]]
    `
});

// Health check endpoint for UptimeRobot
const http = require("http");
const startedAt = Date.now();

http.createServer((req, res) => {
    if (req.url === "/health" && req.method === "GET") {
        const isReady = client.isReady();
        const uptime = Math.floor((Date.now() - startedAt) / 1000);
        const guilds = client.guilds.cache.size;
        const ping = client.ws.ping;

        res.writeHead(isReady ? 200 : 503, { "Content-Type": "application/json" });
        res.end(JSON.stringify({
            status: isReady ? "online" : "offline",
            uptime,
            guilds,
            ping,
        }));
    } else {
        res.writeHead(404);
        res.end();
    }
}).listen(3001, "127.0.0.1", () => {
    console.log("[HEALTH] Listening on http://127.0.0.1:3001/health");
});

client.login(process.env.DANGER_DONTSHARETOYKEN);