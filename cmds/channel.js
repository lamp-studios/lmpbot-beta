module.exports = {
    type: "messageCreate",
    code: `$if[$channelID==$getGuildVar[dont_talk_channel;$guildID];
        $!deleteMessage[$channelID;$messageID]
        $!timeout[$guildID;$userID;1m;Spambot]
        $sendDM[$authorID;Bot detected!!!]
    ;]`,
}