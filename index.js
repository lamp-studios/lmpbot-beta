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

client.functions.add({
    name: "readLargeFile",
    params: ["filepath"],
    code: `
    $return[$djsEval[const fs = require('fs'); const path = require('path'); let result = ''; try { const fullPath = path.resolve('$env[filepath]'); if (fs.existsSync(fullPath)) { result = fs.readFileSync(fullPath, 'utf-8'); } } catch (error) { console.error('Error reading file:', error); } result]]
    `
});

client.login(process.env.DANGER_DONTSHARETOYKEN);