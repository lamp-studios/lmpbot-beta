module.exports = {
    type: "messageCreate",
    name: "verify",
    code: `
$if[$getMemberVar[is_verified;$authorID;$guildID;false]==false;$setMemberVar[is_verified;true;$authorID;$guildID] $memberAddRoles[$guildID;$authorID;$getGuildVar[verification_role;$guildID;$findRole[$guildID;verified]]] Verified successfully!;You are already verified!]`
};