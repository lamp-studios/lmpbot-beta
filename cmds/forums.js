module.exports = {
    type: "threadCreate",
    code: `
$onlyIf[$channelParentID==$getGuildVar[forum_channel;$guildID];]
$log[New forum post created: "$channelName" by $threadOwnerID in <#$channelParentID>]
$sendMessage[$channelID;Adding staff members for visibility...]
$addThreadMember[$guildID;$channelID;$guildOwnerID[$guildID]]
$fetchMembers[$guildID]
$if[$getGuildVar[staff_role;$guildID]==;
$arrayLoad[admins;,;$roleMembers[$guildID;$findRole[$guildID;Admin];,]]
$arrayForEach[admins;uid;$addThreadMember[$guildID;$channelID;$env[uid]]]
;$arrayLoad[admins;,;$roleMembers[$guildID;$getGuildVar[staff_role;$guildID];,]]
$arrayForEach[admins;uid;$addThreadMember[$guildID;$channelID;$env[uid]]]
]
`
}