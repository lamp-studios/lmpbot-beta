module.exports = {
    name: "up",
    type: "messageCreate",
    code: `
$onlyForUsers[;$botOwnerID]
$updateCommands
$updateApplicationCommands
$!addMessageReactions[$channelID;$messageID;👍🏻]
	`
}