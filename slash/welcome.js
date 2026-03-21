module.exports = {
  code: `
$c[$if[$hasPerms[$guildID;$authorID;Administrator];test;no]] $c[extra layer of security hell yeah]
$ephemeral
$defer
$fetchMembers[$guildID]
$arrayLoad[members;, ;$guildMemberIDs[$guildID;, ]]
$arrayForEach[members;i;
$if[$option[mentions]==true;$allowAllMentions;$disableAllMentions]
$sendMessage[$option[channel];Welcome <@$env[i]> to **$guildName[$guildID]**!;false]]
Sending welcome messages...
`,
  data: {
    description: "Resends all welcome messages of all members to a specified channel.",
    default_member_permissions: 8,
    name: "welcome",
    options: [
     {
       name: "channel",
       type: 7,
       channel_types: [
        0],
      description: "The channel to send the messages in.",
      required: true
    },
    {
      type: 5,
      name: "mentions",
      description: "Mentions every members in the messages if true",
      required: true
    },
    {
      type: 3,
      description: "The welcome message",
      name: "welcome-message",
      min_length: 1,
      max_length: 100,
      required: false
    }
  ]
}}