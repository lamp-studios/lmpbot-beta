module.exports = {
type: "threadCreate",
code: `
$if[$channelType[$channelID]==GuildForum;$log[hi]]
`}