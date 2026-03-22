module.exports = {
    type: "threadCreate",
    code: `
$onlyIf[$djsEval[channel.new.parent?.isThreadOnly()]==true;]
$log[New forum post created: "$channelName" by $threadOwnerID in <#$channelParentID>]
`
}