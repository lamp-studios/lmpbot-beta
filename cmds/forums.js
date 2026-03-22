module.exports = {
    type: "threadCreate",
    code: `
$onlyIf[$djsEval[ctx.states?.channel?.new?.parent?.isThreadOnly()]==true;]
$log[New forum post created: "$channelName" by $threadOwnerID in <#$channelParentID>]
$sendMessage[$channelID;Adding staff members for visibility...]
$addThreadMember[$guildID;$channelID;$guildOwnerID[$guildID]]
$arrayLoad[admins;,;$roleMembers[$guildID;$findRole[$guildID;Admin];,]]
$arrayForEach[admins;uid;$addThreadMember[$guildID;$channelID;$env[uid]]]
`
}