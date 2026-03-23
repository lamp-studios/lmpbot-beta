module.exports = {
  code: `
$if[$option[channel]==;
$deleteGuildVar[forum_channel;$guildID]
Removed forum channel from adding admins in new posts!
;$setGuildVar[forum_channel;$option[channel];$guildID]
Set $option[channel] as forum channel successfully!]

$if[$option[role]!=;
$setGuildVar[staff_role;$option[role];$guildID]
Staff role set to <@&$option[role]>!;]
$ephemeral
  `,
  data: {
    name: "set_forum_channel",
    description: "Sets the forum channel where staff are automatically added to new posts.",
    default_member_permissions: 8, // Admin Only
    options: [
      {
        name: "channel",
        description: "Channel to set as a forum channel.",
        type: 7, // CHANNEL
        required: false
      },
      {
        name: "role",
        description: "Role to set (optional).",
        type: 8, // ROLE
        required: false
      }
    ]
  }
};