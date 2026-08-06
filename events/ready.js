import { Events, ActivityType, PresenceUpdateStatus } from "discord.js";
import { startHeartbeat } from "../utils/heartbeat.js";
import { startBirthdayScheduler } from "../utils/birthdays.js";
import { resolveOwnerIds } from "../utils/owner.js";

async function updateStatus(client) {
  const guildCount = client.guilds.cache.size;
  const memberCount = client.guilds.cache.reduce(
    (sum, g) => sum + (g.memberCount || 0),
    0
  );
  await client.user.setPresence({
    status: PresenceUpdateStatus.DoNotDisturb,
    activities: [
      {
        type: ActivityType.Watching,
        name: `${guildCount} servers and ${memberCount} members.`,
      },
    ],
  });
}

export default {
  name: Events.ClientReady,
  once: true,

  async execute(client) {
    console.log("ready");

    // resolve owner id(s) from the application (team members or single owner)
    await resolveOwnerIds(client);

    await updateStatus(client);
    setInterval(() => updateStatus(client).catch(() => {}), 60_000);

    startHeartbeat(client);
    startBirthdayScheduler(client);
  },
};
