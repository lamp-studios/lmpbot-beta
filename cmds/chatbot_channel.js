module.exports = {
    type: "messageCreate",
    code: `$!if[$channelID==$getGuildVar[chatbot_channel;$guildID];
    $fetchApplicationEmojis
    $let[loadingMsgID;$sendMessage[$channelID;Loading... <a:CircleLoader:1492857500637335685>;true]]
    $let[geminiReply;$callFunction[chatGemini;$messageContent]]
    $editMessage[$channelID;$get[loadingMsgID];$get[geminiReply]]
    ;]`,
}