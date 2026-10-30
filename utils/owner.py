# Who owns the bot. The application owner is either a single user or a Discord
# developer team, in which case every team member counts as an owner.
#
# Ids are resolved once at startup (events/ready.py) and cached on
# `bot.owner_ids`; is_bot_owner re-resolves if that cache is somehow empty, so
# an owner-only command can never fall open just because the startup fetch
# failed.


async def resolve_owner_ids(bot) -> set[int]:
    """Fill `bot.owner_ids` from the application. Returns the same set."""
    app = await bot.application_info()
    ids = set(bot.owner_ids or ())
    if app.team:
        ids.update(member.id for member in app.team.members)
    elif app.owner:
        ids.add(app.owner.id)
    bot.owner_ids = ids
    return ids


def is_owner_cached(bot, user_id) -> bool:
    """Owner check against the startup cache only, for prefix commands."""
    return int(user_id) in (bot.owner_ids or ())


async def is_bot_owner(bot, user_id) -> bool:
    """True if the user owns the bot or is on its team."""
    if not bot.owner_ids:
        try:
            await resolve_owner_ids(bot)
        except Exception as err:
            print(f"[owner] couldn't resolve owner ids: {err}")
    return int(user_id) in (bot.owner_ids or ())
