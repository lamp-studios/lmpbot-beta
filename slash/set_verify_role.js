module.exports = {
  code: `
$if[$authorID==$botOwnerID;
$setGuildVar[verification_role;$option[role];$guildID]
Set $option[role] as verified role successfully!
$ephemeral
;You do not have permission!
$ephemeral]`,
  data: {
    name: "set_verification_role",
    description: "Set a verification role (required).",
    default_member_permissions: 8, // Admin Only
    options: [
      {
        name: "role",
        description: "Role to set as verification role.",
        type: 8, // ROLE
        required: true
      }
    ]
  }
};