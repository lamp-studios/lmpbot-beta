# Birthday feature: shared config keys, date helpers, and the daily scheduler.
#
# Dates are intentionally timezone-free. A birthday is stored as a bare
# "DD/MM" string and compared against the bot host's local date, so a server
# running in one place announces on that day's local calendar date.

import asyncio
import re
from datetime import date, datetime

import discord

from utils.db import get_guild_var, get_member_var, search_member_var, set_guild_var

# guild-var keys, grouped so the command and scheduler can't drift apart.
KEYS = {
    "enabled": "birthday_enabled",
    "role": "birthday_role",
    "channel": "birthday_channel",
    "message": "birthday_message",
    "ping_role": "birthday_ping_role",
    "ping_enabled": "birthday_ping_enabled",
    "set_channel": "birthday_set_channel",
    "last_run": "birthday_last_run",
}

MEMBER_KEY = "birthday"

# per-member preference: "false" opts out of private /birthday replies
EPHEMERAL_KEY = "birthday_ephemeral"

DEFAULT_MESSAGE = "🎉 Happy birthday {user}! 🎂"

DAYS_IN_MONTH = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

_DATE = re.compile(r"^(\d{1,2})\s*/\s*(\d{1,2})$")


def parse_date(text) -> str | None:
    """
    Parse loose user input ("30/01", "30/1", "3/1") into a canonical zero-padded
    "DD/MM" string, or None if it isn't a valid day/month. 29/02 is allowed.
    """
    m = _DATE.match(str(text).strip())
    if not m:
        return None
    day = int(m.group(1))
    month = int(m.group(2))
    if month < 1 or month > 12:
        return None
    if day < 1 or day > DAYS_IN_MONTH[month - 1]:
        return None
    return f"{day:02d}/{month:02d}"


def today_key(now: datetime | None = None) -> str:
    """Today's date as "DD/MM" in the host's local time."""
    now = now or datetime.now()
    return f"{now.day:02d}/{now.month:02d}"


def calendar_order(value: str) -> int:
    """Sort key that puts "DD/MM" dates in calendar order, January first."""
    day, month = (int(x) for x in value.split("/"))
    return month * 100 + day


def days_until(value: str, now: datetime | None = None) -> int | None:
    """
    Whole days from today until "DD/MM" next comes round; 0 means today. 29/02
    jumps to the next leap year instead of sliding onto 01/03, so it can be up to
    eight years out, hence the bounded search rather than a single subtraction.
    """
    day, month = (int(x) for x in value.split("/"))
    today = (now or datetime.now()).date()

    for year in range(today.year, today.year + 9):
        try:
            upcoming = date(year, month, day)
        except ValueError:
            continue  # 29/02 in a non-leap year
        if upcoming >= today:
            return (upcoming - today).days
    return None


def _date_stamp(now: datetime | None = None) -> str:
    """Local calendar day as "YYYY-MM-DD"; used to run the scan once per day."""
    return (now or datetime.now()).strftime("%Y-%m-%d")


async def get_config(guild_id) -> dict:
    """Read the whole birthday config for a guild in one shot."""
    enabled, role, channel, message, ping_role, ping_enabled, set_channel = await asyncio.gather(
        get_guild_var(guild_id, KEYS["enabled"]),
        get_guild_var(guild_id, KEYS["role"]),
        get_guild_var(guild_id, KEYS["channel"]),
        get_guild_var(guild_id, KEYS["message"]),
        get_guild_var(guild_id, KEYS["ping_role"]),
        get_guild_var(guild_id, KEYS["ping_enabled"]),
        get_guild_var(guild_id, KEYS["set_channel"]),
    )
    return {
        "enabled": enabled == "true",
        "role_id": role,
        "channel_id": channel,
        "message": message or DEFAULT_MESSAGE,
        "ping_role_id": ping_role,
        "ping_enabled": ping_enabled == "true",
        "set_channel_id": set_channel,
    }


async def get_guild_birthdays(guild_id) -> list[dict]:
    """
    Every stored birthday in one guild as [{"member_id", "date"}], unsorted.
    Anything that no longer parses as a day/month is dropped.
    """
    rows = await search_member_var(MEMBER_KEY)
    return [
        {"member_id": str(row["member_id"]), "date": row["value"]}
        for row in rows
        if str(row["guild_id"]) == str(guild_id) and parse_date(row["value"] or "")
    ]


async def prefers_ephemeral(guild_id, member_id) -> bool:
    """Whether this member wants their /birthday replies kept private. Default yes."""
    return (await get_member_var(guild_id, member_id, EPHEMERAL_KEY)) != "false"


def render_message(template: str | None, member: discord.Member) -> str:
    """Fill placeholders in a custom announcement message."""
    return (
        (template or DEFAULT_MESSAGE)
        .replace("{user}", member.mention)
        .replace("{mention}", member.mention)
        .replace("{name}", member.display_name)
    )


def snowflake(value) -> int | None:
    """A stored id as an int, or None if it isn't one."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


CHECK_INTERVAL_S = 30 * 60  # re-check every 30 minutes
ANNOUNCE_HOUR = 8  # don't announce before 08:00 host-local time


async def _process_guild(guild: discord.Guild, birthdays_by_member: dict, today: str):
    """
    Announce today's birthdays for one guild and reconcile the birthday role
    (grant to today's people, revoke from everyone else who still has it).
    """
    cfg = await get_config(guild.id)
    if not cfg["enabled"]:
        return

    role_id = snowflake(cfg["role_id"])
    channel_id = snowflake(cfg["channel_id"])
    role = guild.get_role(role_id) if role_id else None
    channel = guild.get_channel(channel_id) if channel_id else None

    celebrant_ids = {member_id for member_id, value in birthdays_by_member.items() if value == today}

    # Revoke a stale birthday role before granting today's, so yesterday's
    # celebrants don't keep it. Only touches members who currently hold it.
    if role:
        for member in list(role.members):
            if str(member.id) not in celebrant_ids:
                try:
                    await member.remove_roles(role)
                except Exception:
                    pass

    for member_id in celebrant_ids:
        member_snowflake = snowflake(member_id)
        if member_snowflake is None:
            continue
        try:
            member = await guild.fetch_member(member_snowflake)
        except Exception:
            continue

        if role:
            try:
                await member.add_roles(role)
            except Exception:
                pass

        if isinstance(channel, discord.abc.Messageable):
            ping_role_id = snowflake(cfg["ping_role_id"])
            ping = f"<@&{ping_role_id}> " if cfg["ping_enabled"] and ping_role_id else ""
            try:
                await channel.send(
                    ping + render_message(cfg["message"], member),
                    allowed_mentions=discord.AllowedMentions(
                        everyone=False,
                        users=[member],
                        roles=[discord.Object(ping_role_id)] if ping else False,
                        replied_user=False,
                    ),
                )
            except Exception:
                pass


async def _run_scan(bot):
    now = datetime.now()
    if now.hour < ANNOUNCE_HOUR:
        return

    stamp = _date_stamp(now)
    today = today_key(now)

    # group every stored birthday by guild so we hit the DB once per scan
    by_guild: dict[str, dict[str, str]] = {}
    for row in await search_member_var(MEMBER_KEY):
        by_guild.setdefault(str(row["guild_id"]), {})[str(row["member_id"])] = row["value"]

    for guild in list(bot.guilds):
        # once per day per guild, even across restarts
        last_run = await get_guild_var(guild.id, KEYS["last_run"])
        if last_run == stamp:
            continue

        cfg = await get_config(guild.id)
        if not cfg["enabled"]:
            continue

        await set_guild_var(guild.id, KEYS["last_run"], stamp)
        try:
            await _process_guild(guild, by_guild.get(str(guild.id), {}), today)
        except Exception as err:
            print(f"[birthdays] scan failed for guild {guild.id}: {err}")


_task: asyncio.Task | None = None


async def _loop(bot):
    while True:
        try:
            await _run_scan(bot)
        except Exception as err:
            print(f"[birthdays] {err!r}")
        await asyncio.sleep(CHECK_INTERVAL_S)


def start_birthday_scheduler(bot):
    """Start the once-a-day birthday scan loop."""
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_loop(bot))
        print("[birthdays] scheduler started")


def is_admin(ctx: discord.ApplicationContext) -> bool:
    """True if the interacting member may change server-wide birthday settings."""
    perms = ctx.interaction.permissions
    return bool(perms and perms.administrator)
