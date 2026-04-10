module.exports = {
  code: `
$if[$option[channel]==;
$deleteGuildVar[news_channel;$guildID]
Removed channel from having bot news sent in.
;$setGuildVar[news_channel;$option[channel];$guildID]
Set $option[channel] as news channel successfully!]
$ephemeral
  `,
  data: {
    name: "set_news_channel",
    description: "Sets the news channel where bot news are sent in.",
    default_member_permissions: 8, // Admin Only
    options: [
      {
        name: "channel",
        description: "Channel to set as a bot news channel.",
        type: 7, // CHANNEL
        required: false
      }
    ]
  }
};