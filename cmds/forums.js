module.exports = {
type: "channelCreate",
code: `
$if[$channelType[$channelID]==GuildForum;$log[hi]]
`}