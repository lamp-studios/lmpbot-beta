module.exports = {
type: "channelCreate",
code: `
$if[$channelType[$channelID]==PublicThread;$djsEval[console.log("hi")]]
`}