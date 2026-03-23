module.exports = {
    type: "threadCreate",
    code: `
$onlyIf[$channelParentID==1479207101237694518;]
$log[New forum post created: "$channelName" by $threadOwnerID in <#$channelParentID>]
$sendMessage[$channelID;Adding staff members for visibility...]
$addThreadMember[$guildID;$channelID;$guildOwnerID[$guildID]]
$fetchMembers[$guildID]
$arrayLoad[admins;,;$roleMembers[$guildID;$findRole[$guildID;Admin];,]]
$arrayForEach[admins;uid;$addThreadMember[$guildID;$channelID;$env[uid]]]
`
}