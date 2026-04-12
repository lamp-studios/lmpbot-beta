module.exports = {
    type: "messageCreate",
    code: `$!if[$channelID==$getGuildVar[chatbot_channel;$guildID];
    $fetchApplicationEmojis
    Loading... <a:CircleLoader:1492857500637335685>
    $callFunction[chatGemini;$messageContent]
    ;]`,
}