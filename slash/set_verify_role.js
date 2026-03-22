module.exports = {
  code: `
$if[$option[role]==;
$deleteGuildVar[verification_role;$guildID]
Removed verification role!
$ephemeral;
$setGuildVar[verification_role;$option[role];$guildID]
Set $option[role] as verified role successfully!
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
        required: false
      }
    ]
  }
};