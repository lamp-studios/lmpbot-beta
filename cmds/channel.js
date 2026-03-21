module.exports = {
    type: "messageCreate",
    code: `$!if[$channelID==$getGuildVar[dont_talk_channel;$guildID];
        $!deleteMessage[$channelID;$messageID]
        $c[$!timeout[$guildID;$userID;1m;Spambot]]
        $!setMemberVar[strike;1;$authorID;$guildID]
        $!sendDM[$authorID;Bot detected!!!]
        $!kickMember[$guildID;$authorID;spambot detected]
    ;]`,
}