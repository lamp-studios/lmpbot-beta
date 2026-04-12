module.exports = {
    type: "messageCreate",
    code: `$!if[$channelID==$getGuildVar[chatbot_channel;$guildID];
    $callFunction[chatGemini;$messageContent]
    ;]`,
}