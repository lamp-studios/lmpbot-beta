module.exports = {
  code: `
$if[$option[channel]==;
$deleteGuildVar[chatbot_channel;$guildID]
Removed chatbot channel!
$ephemeral
;$setGuildVar[chatbot_channel;$option[channel];$guildID]
Set $option[channel] as chatbot channel successfully!
$ephemeral]
  `,
  data: {
    name: "set_chatbot_channel",
    description: "Set a channel to have an AI in.",
    default_member_permissions: 8, // Admin Only
    options: [
      {
        name: "channel",
        description: "Channel to set as a chatbot channel.",
        type: 7, // CHANNEL
        required: false
      }
    ]
  }
};