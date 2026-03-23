module.exports = {
    type: "threadCreate",
    code: `
$onlyIf[$channelParentID==$getGuildVar[forum_channel;$guildID];]
$log[New forum post created: "$channelName" by $threadOwnerID in <#$channelParentID>]
$sendMessage[$channelID;Adding staff members for visibility...]
$addThreadMember[$guildID;$channelID;$guildOwnerID[$guildID]]
$let[role;$getGuildVar[staff_role;$guildID]]
$if[$get[role]==;$let[role;$findRole[$guildID;Admin]];]
$arrayLoad[admins;,;$roleMembers[$guildID;$get[role];,]]
$arrayForEach[admins;uid;$addThreadMember[$guildID;$channelID;$env[uid]]]
`
}