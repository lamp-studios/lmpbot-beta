// Who owns the bot. The application owner is either a single user or a Discord
// developer team, in which case every team member counts as an owner.
//
// Ids are resolved once at startup (events/ready.js) and cached on the client;
// isBotOwner re-resolves if that cache is somehow empty, so an owner-only
// command can never fall open just because the startup fetch failed.

/**
 * Fill `client.ownerIds` from the application.
 * @returns {Promise<Set<string>>} the same set, for convenience
 */
export async function resolveOwnerIds(client) {
  const app = await client.application.fetch();
  if (app.owner) {
    if (app.owner.members) {
      for (const id of app.owner.members.keys()) client.ownerIds.add(id);
    } else {
      client.ownerIds.add(app.owner.id);
    }
  }
  return client.ownerIds;
}

/** @returns {Promise<boolean>} true if the user owns the bot or is on its team */
export async function isBotOwner(client, userId) {
  if (client.ownerIds.size === 0) {
    await resolveOwnerIds(client).catch((err) => {
      console.warn(`[owner] couldn't resolve owner ids: ${err?.message ?? err}`);
    });
  }
  return client.ownerIds.has(userId);
}
