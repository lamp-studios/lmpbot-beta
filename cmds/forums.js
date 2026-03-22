module.exports = {
type: "channelCreate",
code: `
$if[$channelType[$channelID]==PublicThread;hi]
`}