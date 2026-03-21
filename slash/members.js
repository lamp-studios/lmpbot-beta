module.exports = {
  code: `
$arrayLoad[members;, ;$guildMemberIDs[$guildID;, ]]
$arrayMap[members;member;
  $if[$getMemberVar[is_verified;$env[member];$guildID;false];
    $disableAllMentions
    $return[<@$env[member]>]
  ]
;sortedMembers]
$if[$arrayLength[sortedMembers]==0;
  $arrayPush[sortedMembers;None]
]
$addTextDisplay[$arrayJoin[sortedMembers;\n]]
  `,
  data: {
    name: "members",
    description: "See all verified members.",
  }
};