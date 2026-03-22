module.exports = {
  code: `
$setGuildVar[dont_talk_channel;$option[channel];$guildID]
Set $option[channel] as dont_talk channel successfully!
$ephemeral
  `,
  data: {
    name: "set_bot_channel",
    description: "Set a channel to detect people as bots (required).",
    default_member_permissions: 8, // Admin Only
    options: [
      {
        name: "channel",
        description: "Channel to set as a dont talk channel.",
        type: 7, // CHANNEL
        required: true
      }
    ]
  }
};