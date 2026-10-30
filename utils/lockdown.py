# Server lockdown: hide every channel from a role except one, and be able to put
# it all back.
#
# The role defaults to @everyone but can be any role, because plenty of servers
# gate access behind a "member" role that grants View Channel explicitly, and a
# deny on @everyone does nothing to those people. Each locked role is recorded
# on its own, so a second /lockdown can cover another role without disturbing
# the first, and one /undolockdown lifts the lot.
#
# Only the target role's "View Channel" bit is touched, and only on channels the
# bot can already manage, so every other overwrite survives untouched. What that
# bit was per channel is stored as JSON in a guild var, which is what makes the
# undo exact: a channel that was explicitly allowed goes back to allowed, a
# neutral one goes back to neutral. Channels where the role was *already* denied
# are skipped entirely, so an undo can never open up a private channel that the
# lockdown had nothing to do with.

import asyncio
import json
import time

import discord

from utils.db import delete_guild_var, get_guild_var, set_guild_var

STATE_KEY = "lockdown_state"

# the target role's View Channel bit as stored per channel
ALLOW = "a"
DENY = "d"
NEUTRAL = "n"

TO_VALUE = {ALLOW: True, DENY: False, NEUTRAL: None}

# How many channels are edited at once. Overwrite edits are rate limited per
# channel rather than per guild, so a small fan-out is far quicker than going
# one at a time without pushing at the global limit on a big server.
BATCH = 5

VERSION = 2

# Stored lockdown state (ids are strings, the same JSON the bot has always written):
# {
#   "v": 2,
#   "at": epoch ms,
#   "by": user id,
#   "targets": [
#     {
#       "roleId": ...,
#       "exceptionId": channel id | null,
#       "channels": { channelId: "a" | "d" | "n" },  # bit to restore
#     },
#   ],
#   "botPins": { channelId: "new" | "bit" }           # overwrites we added for ourselves
# }


def _normalize(state, guild_id):
    """Bring the pre-role state shape forward; it was always an @everyone lockdown."""
    if not state or isinstance(state.get("targets"), list):
        return state
    return {
        **state,
        "v": VERSION,
        # the @everyone role always shares the guild's id
        "targets": [
            {
                "roleId": str(guild_id),
                "exceptionId": state.get("exceptionId"),
                "channels": state.get("channels") or {},
            }
        ],
        "botPins": state.get("botPins") or {},
    }


async def read_lockdown(guild_id):
    raw = await get_guild_var(guild_id, STATE_KEY)
    if not raw:
        return None
    try:
        return _normalize(json.loads(raw), guild_id)
    except Exception as err:
        print(f"[lockdown] unreadable state for guild {guild_id}: {err}")
        return None


async def save_lockdown(guild_id, state):
    await set_guild_var(guild_id, STATE_KEY, json.dumps(state, separators=(",", ":"), ensure_ascii=False))


async def clear_lockdown(guild_id):
    await delete_guild_var(guild_id, STATE_KEY)


def locked_role_ids(state) -> list[str]:
    """Ids of every role a lockdown is currently holding down."""
    return [str(t["roleId"]) for t in (state or {}).get("targets") or []]


def _lockable(guild: discord.Guild):
    """Every channel a lockdown can touch. guild.channels never includes threads."""
    return [c for c in guild.channels if not isinstance(c, discord.Thread)]


def _view_state(channel, role) -> str:
    """One role's View Channel bit on one channel, right now."""
    value = channel.overwrites_for(role).view_channel
    if value is True:
        return ALLOW
    if value is False:
        return DENY
    return NEUTRAL


def manageable(channel, me: discord.Member) -> bool:
    """Whether the bot can edit this channel's overwrites at all."""
    perms = channel.permissions_for(me)
    return bool(perms.view_channel and perms.manage_roles)


def _bot_keeps_access(channel, me: discord.Member, target: discord.Role) -> bool:
    """
    Whether the bot would still see a channel once `target` is denied there.
    A deny reaches the bot through any role it holds, so when the bot is in the
    role being locked down it needs an administrator role or an allow of its own,
    or it loses access to the very channel it has to undo later.
    """
    if me.guild_permissions.administrator:
        return True
    # me.roles includes @everyone, so this covers the default target too
    if target.id not in {r.id for r in me.roles}:
        return True

    mine = {me.id, *(r.id for r in me.roles)}
    mine.discard(target.id)

    for who, overwrite in channel.overwrites.items():
        if who.id in mine and overwrite.view_channel is True:
            return True
    return False


async def _set_view(channel, target, value, reason):
    """Set only `target`'s View Channel bit on a channel, keeping the rest of its overwrite."""
    overwrite = channel.overwrites_for(target)
    overwrite.view_channel = value
    await channel.set_permissions(target, overwrite=overwrite, reason=reason)


async def _pin_bot_access(channel, me: discord.Member, reason) -> str:
    """
    Give the bot an explicit View Channel allow so the deny about to land can't
    lock it out. Returns how to clean it up again: "new" if the whole overwrite is
    ours to delete, "bit" if we only added to one that was already there.
    """
    existed = any(who.id == me.id for who in channel.overwrites)
    await _set_view(channel, me, True, reason)
    return "bit" if existed else "new"


async def _in_batches(items, fn):
    for i in range(0, len(items), BATCH):
        await asyncio.gather(*(fn(item) for item in items[i:i + BATCH]))


def name_list(channels, limit=5) -> str:
    """A few channel names for a report, trimmed so a big server can't overflow it."""
    shown = ", ".join(f"#{c.name}" for c in channels[:limit])
    left = len(channels) - limit
    return f"{shown} and {left} more" if left > 0 else shown


async def apply_lockdown(guild: discord.Guild, *, role, exception, user, reason, previous=None):
    """
    Hide every channel from `role` (default @everyone), apart from `exception`.

    `previous` is an existing lockdown to fold this one into, so a second role can
    be locked down without losing the first role's saved permissions.

    Returns {"state", "target", "hidden", "already_hidden", "skipped", "failed",
    "exception_was_hidden"}. `state` is None when nothing was changed, so no
    lockdown gets recorded.
    """
    me = guild.me
    target = role or guild.default_role

    record = {"roleId": str(target.id), "exceptionId": str(exception.id) if exception else None, "channels": {}}
    pins = {}

    targets = []
    skipped = []
    already_hidden = 0

    for channel in _lockable(guild):
        if exception and channel.id == exception.id:
            continue
        if not manageable(channel, me):
            skipped.append(channel)
            continue
        # already invisible to the role: leave it be, so undoing can't reveal it
        if _view_state(channel, target) == DENY:
            already_hidden += 1
            continue
        targets.append(channel)

    hidden = []
    failed = []

    async def hide(channel):
        before = _view_state(channel, target)
        try:
            if not _bot_keeps_access(channel, me, target):
                # recorded before the deny lands, so a half-done channel still cleans up
                pins[str(channel.id)] = await _pin_bot_access(channel, me, reason)
            await _set_view(channel, target, False, reason)
            record["channels"][str(channel.id)] = before
            hidden.append(channel)
        except Exception as err:
            print(f"[lockdown] {guild.id}/{channel.id} failed: {err}")
            failed.append(channel)

    await _in_batches(targets, hide)

    # The exception goes last and is allowed explicitly rather than left alone, so
    # it is visible whatever it inherited before.
    exception_was_hidden = False
    if exception:
        before = _view_state(exception, target)
        exception_was_hidden = before == DENY
        if before != ALLOW:
            try:
                await _set_view(exception, target, True, reason)
                record["channels"][str(exception.id)] = before
            except Exception as err:
                print(f"[lockdown] {guild.id} exception failed: {err}")
                failed.append(exception)

    touched = len(record["channels"]) + len(pins)
    state = None
    if touched:
        state = {
            "v": VERSION,
            "at": int(time.time() * 1000),
            "by": str(user.id),
            "targets": [*((previous or {}).get("targets") or []), record],
            # an earlier pin is the one that created the overwrite, so it wins
            "botPins": {**pins, **((previous or {}).get("botPins") or {})},
        }

    return {
        "state": state,
        "target": target,
        "hidden": hidden,
        "already_hidden": already_hidden,
        "skipped": skipped,
        "failed": failed,
        "exception_was_hidden": exception_was_hidden,
    }


def _channel(guild: discord.Guild, channel_id):
    try:
        return guild.get_channel(int(channel_id))
    except (TypeError, ValueError):
        return None


async def restore_lockdown(guild: discord.Guild, state, reason):
    """
    Put back every View Channel bit the lockdown changed, for every role it holds.

    Returns {"restored", "roles", "gone_roles", "missing", "failed", "remaining"}.
    `remaining` is a trimmed state covering only what failed, so it can be saved
    and retried instead of leaving channels stuck hidden with nothing left to undo
    them with.
    """
    me = guild.me

    restored = []
    missing = []
    failed = []
    roles = []
    gone_roles = []
    targets_left = []
    stuck = set()

    for target in state.get("targets") or []:
        try:
            role = guild.get_role(int(target["roleId"]))
        except (TypeError, ValueError):
            role = None
        if role is None:
            # Discord drops a role's overwrites along with the role itself
            gone_roles.append(target["roleId"])
            continue
        roles.append(role)

        leftover = {}

        async def restore(item, role=role, leftover=leftover):
            channel_id, before = item
            channel = _channel(guild, channel_id)
            if channel is None:
                missing.append(channel_id)
                return
            try:
                await _set_view(channel, role, TO_VALUE.get(before), reason)
                restored.append(channel)
            except Exception as err:
                print(f"[lockdown] undo {guild.id}/{channel_id} failed: {err}")
                failed.append(channel)
                leftover[channel_id] = before
                stuck.add(channel_id)

        await _in_batches(list((target.get("channels") or {}).items()), restore)

        if leftover:
            targets_left.append({**target, "channels": leftover})

    # Our own access comes off only where every role is already back, otherwise a
    # retry would have no way in.
    pins_left = {}

    async def unpin(item):
        channel_id, kind = item
        if channel_id in stuck:
            pins_left[channel_id] = kind
            return
        channel = _channel(guild, channel_id)
        if channel is None:
            return
        try:
            if kind == "new":
                await channel.set_permissions(me, overwrite=None, reason=reason)
            else:
                await _set_view(channel, me, None, reason)
        except Exception as err:
            print(f"[lockdown] undo pin {guild.id}/{channel_id} failed: {err}")

    await _in_batches(list((state.get("botPins") or {}).items()), unpin)

    remaining = {**state, "targets": targets_left, "botPins": pins_left} if targets_left else None

    return {
        "restored": restored,
        "roles": roles,
        "gone_roles": gone_roles,
        "missing": missing,
        "failed": failed,
        "remaining": remaining,
    }
