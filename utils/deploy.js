/**
 * Register/update all loaded slash commands globally.
 * Mirrors the old `.up` behaviour (sync_commands).
 * @param {import("discord.js").Client} client
 * @returns {Promise<number>} number of commands registered
 */
export async function registerCommands(client) {
  const data = [...client.commands.values()].map((c) => c.data.toJSON());
  await client.application.commands.set(data);
  return data.length;
}
