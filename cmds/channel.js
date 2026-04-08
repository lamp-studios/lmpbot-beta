module.exports = {
    type: "messageCreate",
    code: `$!if[$channelID==$getGuildVar[dont_talk_channel;$guildID];
        $!deleteMessage[$channelID;$messageID]
        $c[$!timeout[$guildID;$userID;1m;Spambot]]
        $!setMemberVar[strike;1;$authorID;$guildID]
        $!sendDM[$authorID;Bot detected!!!]
        $!ban[$guildID;$authorID;spambot detected;120]
        $!unban[$guildID;$authorID;spambot detection unban system]
    ;]`,
}