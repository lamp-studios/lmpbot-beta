# Discord sends mentions down the wire as <@123456789>, which tells a language
# model nothing. These helpers rewrite them as
#   @username (display name, id: 123456789)
# so the model can tell people apart, address them by name, and mention them
# back by id if it needs to. The rewritten text is what gets stored in chat
# memory too, so old turns stay readable.

import re

USER_MENTION = re.compile(r"<@!?(\d+)>")


def format_user(user_id, user: dict | None = None) -> str:
    """`user` is {"username", "display_name"}, or None for someone unknown."""
    if not user or not user.get("username"):
        return f"@unknown-user (id: {user_id})"
    username = user["username"]
    display_name = user.get("display_name")
    if display_name and display_name != username:
        return f"@{username} ({display_name}, id: {user_id})"
    return f"@{username} (id: {user_id})"


def replace_user_mentions(content, lookup: dict) -> str:
    """
    Rewrite every user mention using an id -> user lookup. Ids that aren't in the
    lookup still get rewritten, as unknown-user, so no raw <@id> reaches the model.
    """
    return USER_MENTION.sub(lambda m: format_user(m.group(1), lookup.get(m.group(1))), str(content or ""))


def describe_user(user, member=None) -> str:
    """A user as the model should see them, preferring their nickname in this guild."""
    return format_user(
        user.id,
        {
            "username": user.name,
            "display_name": member.display_name if member else (user.display_name or user.name),
        },
    )


async def resolve_mentions(content, message, client) -> str:
    """
    Resolve every user mention in a message's content. Members are looked up in
    the guild first (for nicknames) and fetched only when they aren't cached;
    a lookup that fails leaves the mention as unknown-user rather than raising.
    """
    text = str(content or "")
    ids = [m.group(1) for m in USER_MENTION.finditer(text)]
    if not ids:
        return text

    guild = message.guild
    mentioned = {str(u.id): u for u in message.mentions}

    lookup = {}
    for user_id in dict.fromkeys(ids):
        snowflake = int(user_id)

        member = None
        if guild:
            member = guild.get_member(snowflake)
            if member is None:
                try:
                    member = await guild.fetch_member(snowflake)
                except Exception:
                    member = None

        user = member or mentioned.get(user_id) or client.get_user(snowflake)
        if user is None:
            try:
                user = await client.fetch_user(snowflake)
            except Exception:
                user = None

        if user:
            lookup[user_id] = {
                "username": user.name,
                "display_name": member.display_name if member else user.display_name,
            }

    return replace_user_mentions(text, lookup)
