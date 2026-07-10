import { Events } from "discord.js";
import { getGuildVar } from "../utils/db.js";

export default {
  name: Events.ThreadCreate,

  async execute(thread) {
    if (!thread.guild || !thread.parent) return;

    const forumId = await getGuildVar(thread.guild.id, "forum_channel");
    if (!forumId || thread.parent.id !== forumId) return;

    console.log(
      `New forum post created: "${thread.name}" by ${thread.ownerId} in #${thread.parent.name}`
    );

    // add guild owner
    const owner = await thread.guild.fetchOwner();
    if (owner) await thread.members.add(owner.id);

    // resolve staff role
    const roleId = await getGuildVar(thread.guild.id, "staff_role");
    const role = roleId
      ? thread.guild.roles.cache.get(roleId)
      : thread.guild.roles.cache.find((r) => r.name === "Admin");

    if (role) {
      await thread.guild.members.fetch();
      for (const member of role.members.values()) {
        await thread.members.add(member.id);
      }
    }

    await thread.send("Staff members have been added!");
  },
};
