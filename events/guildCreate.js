import { Events } from "discord.js";

export default {
  name: Events.GuildCreate,

  async execute(guild) {
    console.log(`${guild.name} now has the bot!`);
  },
};
