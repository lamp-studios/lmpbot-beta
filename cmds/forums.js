module.exports = {
    type: "threadCreate",
    code: `
$onlyIf[$djsEval[ctx.states?.channel?.new?.parent?.isThreadOnly()]==true;]
$log[New forum post created: "$channelName" by $threadOwnerID in <#$channelParentID>]
`
}