// Discord sends mentions down the wire as <@123456789>, which tells a language
// model nothing. These helpers rewrite them as
//   @username (display name, id: 123456789)
// so the model can tell people apart, address them by name, and mention them
// back by id if it needs to. The rewritten text is what gets stored in chat
// memory too, so old turns stay readable.

const USER_MENTION = /<@!?(\d+)>/g;

/**
 * @param {string} id
 * @param {{username?: string, displayName?: string}} [user]
 */
export function formatUser(id, user) {
  if (!user?.username) return `@unknown-user (id: ${id})`;
  const { username, displayName } = user;
  return displayName && displayName !== username
    ? `@${username} (${displayName}, id: ${id})`
    : `@${username} (id: ${id})`;
}

/**
 * Rewrite every user mention using an id -> user lookup. Ids that aren't in the
 * lookup still get rewritten, as unknown-user, so no raw <@id> reaches the model.
 * @param {string} content
 * @param {Map<string, {username: string, displayName?: string}>} lookup
 */
export function replaceUserMentions(content, lookup) {
  return String(content ?? "").replace(USER_MENTION, (_match, id) =>
    formatUser(id, lookup.get(id))
  );
}

/** A user as the model should see them, preferring their nickname in this guild. */
export function describeUser(user, member) {
  return formatUser(user.id, {
    username: user.username,
    displayName: member?.displayName ?? user.displayName ?? user.username,
  });
}

/**
 * Resolve every user mention in a message's content. Members are looked up in
 * the guild first (for nicknames) and fetched only when they aren't cached;
 * a lookup that fails leaves the mention as unknown-user rather than throwing.
 * @param {string} content
 * @param {import("discord.js").Message} message
 * @returns {Promise<string>}
 */
export async function resolveMentions(content, message) {
  const ids = [...String(content ?? "").matchAll(USER_MENTION)].map((m) => m[1]);
  if (ids.length === 0) return String(content ?? "");

  const lookup = new Map();
  for (const id of new Set(ids)) {
    const member =
      message.guild?.members.cache.get(id) ??
      (await message.guild?.members.fetch(id).catch(() => null)) ??
      null;

    const user =
      member?.user ??
      message.mentions?.users?.get(id) ??
      message.client?.users?.cache?.get(id) ??
      (await message.client?.users?.fetch(id).catch(() => null)) ??
      null;

    if (user) lookup.set(id, { username: user.username, displayName: member?.displayName ?? user.displayName });
  }

  return replaceUserMentions(content, lookup);
}
