from datetime import datetime

import discord
from discord.ext import commands

from utils.birthdays import (
    DEFAULT_MESSAGE,
    EPHEMERAL_KEY,
    KEYS,
    MEMBER_KEY,
    calendar_order,
    days_until,
    get_config,
    get_guild_birthdays,
    is_admin,
    parse_date,
    prefers_ephemeral,
)
from utils.db import set_guild_var, set_member_var

ADMIN_ONLY = "You need the **Administrator** permission to do that."
DISABLED = "The birthday feature is currently disabled on this server."

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# leaves room under Discord's 2000-character limit for the overflow note
MAX_LEN = 1800

NO_MENTIONS = discord.AllowedMentions.none()


async def private(ctx: discord.ApplicationContext, content: str):
    """Denials and input errors, which stay private whatever the preference."""
    await ctx.respond(content, ephemeral=True)


async def for_member(ctx: discord.ApplicationContext, content: str):
    """
    Successful output: private only if the member asked for that. Mentions are
    never resolved, because a public settings summary would otherwise ping every
    role it lists.
    """
    priv = await prefers_ephemeral(ctx.guild.id, ctx.author.id)
    await ctx.respond(content, ephemeral=priv, allowed_mentions=NO_MENTIONS)


async def collect(guild: discord.Guild):
    """
    Resolve stored birthdays to members who are still on the server. Rows for
    members who left are dropped.
    """
    stored = await get_guild_birthdays(guild.id)
    try:
        members = guild.members if guild.chunked else await guild.chunk()
        member_ids = {str(m.id) for m in members}
    except Exception:
        member_ids = None

    return [
        {**row, "mention": f"<@{row['member_id']}>"}
        for row in stored
        if member_ids is None or row["member_id"] in member_ids
    ]


def render_list(entries) -> str:
    """Calendar-ordered birthdays under a heading per month, trimmed to fit one message."""
    lines = ["# Birthdays"]
    used = len(lines[0])
    month = None
    shown = 0

    for entry in entries:
        name = MONTHS[int(entry["date"][3:]) - 1]
        chunk = [] if name == month else [f"\n**{name}**"]
        chunk.append(f"- `{entry['date']}` {entry['mention']}")

        cost = len("\n".join(chunk)) + 1
        if used + cost > MAX_LEN:
            break

        lines.extend(chunk)
        used += cost
        month = name
        shown += 1

    left = len(entries) - shown
    if left > 0:
        lines.append(f"\n*…and {left} more. Ask again with `/birthday upcoming`.*")
    return "\n".join(lines)


def render_upcoming(entries, window: int) -> str:
    """The soonest birthdays first, labelled by how far off they are."""

    def when(days):
        if days == 0:
            return "**today** 🎂"
        if days == 1:
            return "**tomorrow**"
        return f"in **{days}** days"

    lines = ["# Upcoming birthdays", f"Next **{window}** {'day' if window == 1 else 'days'}."]
    used = len("\n".join(lines))
    shown = 0

    for entry in entries:
        line = f"- `{entry['date']}` {entry['mention']}: {when(entry['days'])}"
        if used + len(line) + 1 > MAX_LEN:
            break
        lines.append(line)
        used += len(line) + 1
        shown += 1

    left = len(entries) - shown
    if left > 0:
        lines.append(f"\n*…and {left} more.*")
    return "\n".join(lines)


async def settings_summary(guild_id) -> str:
    """The current guild config as markdown."""
    cfg = await get_config(guild_id)

    def role_or_none(value):
        return f"<@&{value}>" if value else "*none*"

    def channel_or_none(value):
        return f"<#{value}>" if value else "*none*"

    message = "*default*" if cfg["message"] == DEFAULT_MESSAGE else f"`{cfg['message']}`"
    lines = [
        "# Birthday settings",
        f"- Feature: **{'enabled' if cfg['enabled'] else 'disabled'}**",
        f"- Birthday role: {role_or_none(cfg['role_id'])}",
        f"- Announcement channel: {channel_or_none(cfg['channel_id'])}",
        f"- Ping role: {role_or_none(cfg['ping_role_id'])} (ping {'on' if cfg['ping_enabled'] else 'off'})",
        f"- /birthday set channel: {channel_or_none(cfg['set_channel_id']) if cfg['set_channel_id'] else '*anywhere*'}",
        f"- Message: {message}",
    ]
    return "\n".join(lines)


class Birthday(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    birthday = discord.SlashCommandGroup("birthday", "Birthday announcements and roles.")

    @birthday.command(name="set", description="Set your birthday, e.g. /birthday set 30/01 (day/month).")
    async def set_birthday(
        self,
        ctx: discord.ApplicationContext,
        date: discord.Option(str, description="Your birthday as day/month, e.g. 30/01", required=True),
    ):
        guild_id = ctx.guild.id
        cfg = await get_config(guild_id)
        if not cfg["enabled"]:
            return await private(ctx, DISABLED)
        if cfg["set_channel_id"] and str(ctx.channel.id) != cfg["set_channel_id"]:
            return await private(ctx, f"Please use <#{cfg['set_channel_id']}> to set your birthday.")

        parsed = parse_date(date)
        if not parsed:
            return await private(ctx, f"`{date}` isn't a valid day/month. Try something like `30/01`.")

        await set_member_var(guild_id, ctx.author.id, MEMBER_KEY, parsed)
        await for_member(ctx, f"Your birthday is set to **{parsed}** (day/month). 🎂")

    @birthday.command(name="list", description="See everyone's birthday on this server, in calendar order.")
    async def list_birthdays(self, ctx: discord.ApplicationContext):
        guild_id = ctx.guild.id
        cfg = await get_config(guild_id)
        if not cfg["enabled"]:
            return await private(ctx, DISABLED)

        priv = await prefers_ephemeral(guild_id, ctx.author.id)
        await ctx.defer(ephemeral=priv)

        entries = await collect(ctx.guild)
        entries.sort(key=lambda e: calendar_order(e["date"]))

        text = render_list(entries) if entries else "Nobody has set a birthday yet. Be the first with `/birthday set`."
        await ctx.edit(content=text, allowed_mentions=NO_MENTIONS)

    @birthday.command(name="upcoming", description="See the birthdays coming up soon.")
    async def upcoming(
        self,
        ctx: discord.ApplicationContext,
        days: discord.Option(
            int,
            description="How many days ahead to look. Defaults to 30.",
            required=False,
            default=None,
            min_value=1,
            max_value=365,
        ),
    ):
        guild_id = ctx.guild.id
        cfg = await get_config(guild_id)
        if not cfg["enabled"]:
            return await private(ctx, DISABLED)

        window = days if days is not None else 30
        priv = await prefers_ephemeral(guild_id, ctx.author.id)
        await ctx.defer(ephemeral=priv)

        # one `now` for the whole list, so a scan crossing midnight stays consistent
        now = datetime.now()
        entries = [{**e, "days": days_until(e["date"], now)} for e in await collect(ctx.guild)]
        entries = [e for e in entries if e["days"] is not None and e["days"] <= window]
        entries.sort(key=lambda e: (e["days"], calendar_order(e["date"])))

        if entries:
            text = render_upcoming(entries, window)
        else:
            text = (
                f"No birthdays in the next **{window}** {'day' if window == 1 else 'days'}. "
                "Try `/birthday list` for all of them."
            )
        await ctx.edit(content=text, allowed_mentions=NO_MENTIONS)

    @birthday.command(name="visibility", description="Choose who sees your /birthday replies. Run with no option to view.")
    async def visibility(
        self,
        ctx: discord.ApplicationContext,
        mode: discord.Option(
            str,
            description="Keep replies to yourself, or post them in the channel.",
            required=False,
            default=None,
            choices=[
                discord.OptionChoice(name="Only me (ephemeral)", value="ephemeral"),
                discord.OptionChoice(name="Everyone (public)", value="public"),
            ],
        ),
    ):
        guild_id = ctx.guild.id

        if mode is None:
            priv = await prefers_ephemeral(guild_id, ctx.author.id)
            return await private(
                ctx,
                f"Your `/birthday` replies are currently **{'only visible to you' if priv else 'posted publicly'}**. "
                "Change it with `/birthday visibility`.",
            )

        await set_member_var(guild_id, ctx.author.id, EPHEMERAL_KEY, "true" if mode == "ephemeral" else "false")
        await private(
            ctx,
            "Your `/birthday` replies will only be visible to you."
            if mode == "ephemeral"
            else "Your `/birthday` replies will now be posted in the channel for everyone to see.",
        )

    @birthday.command(name="settings", description="(Admin) View or change birthday settings. Run with no options to view.")
    async def settings(
        self,
        ctx: discord.ApplicationContext,
        role: discord.Option(
            discord.Role, description="Role given to a member on their birthday.", required=False, default=None
        ),
        channel: discord.Option(
            discord.TextChannel,
            description="Channel where birthdays are announced.",
            required=False,
            default=None,
        ),
        message: discord.Option(
            str, description="Custom announcement. Placeholders: {user}, {name}.", required=False, default=None
        ),
        ping_role: discord.Option(
            discord.Role, description="Role to ping in announcements.", required=False, default=None
        ),
        ping: discord.Option(
            bool, description="Turn the announcement ping on or off.", required=False, default=None
        ),
        set_channel: discord.Option(
            discord.TextChannel,
            description="Channel where members must run /birthday set.",
            required=False,
            default=None,
        ),
    ):
        guild_id = ctx.guild.id
        if not is_admin(ctx):
            return await private(ctx, ADMIN_ONLY)

        no_changes = all(v is None for v in (role, channel, message, ping_role, ping, set_channel))
        if no_changes:
            return await for_member(ctx, await settings_summary(guild_id))

        changes = []
        if role:
            await set_guild_var(guild_id, KEYS["role"], role.id)
            changes.append(f"Birthday role → {role.mention}")
        if channel:
            await set_guild_var(guild_id, KEYS["channel"], channel.id)
            changes.append(f"Announcement channel → {channel.mention}")
        if message is not None:
            await set_guild_var(guild_id, KEYS["message"], message)
            changes.append("Custom message updated")
        if ping_role:
            await set_guild_var(guild_id, KEYS["ping_role"], ping_role.id)
            await set_guild_var(guild_id, KEYS["ping_enabled"], "true")
            changes.append(f"Ping role → {ping_role.mention} (ping on)")
        if ping is not None:
            await set_guild_var(guild_id, KEYS["ping_enabled"], "true" if ping else "false")
            changes.append(f"Announcement ping → {'on' if ping else 'off'}")
        if set_channel:
            await set_guild_var(guild_id, KEYS["set_channel"], set_channel.id)
            changes.append(f"/birthday set channel → {set_channel.mention}")

        await for_member(ctx, "Updated:\n- " + "\n- ".join(changes))

    @birthday.command(name="enable", description="(Admin) Enable the birthday feature.")
    async def enable(self, ctx: discord.ApplicationContext):
        await self.toggle(ctx, True)

    @birthday.command(name="disable", description="(Admin) Disable the birthday feature.")
    async def disable(self, ctx: discord.ApplicationContext):
        await self.toggle(ctx, False)

    async def toggle(self, ctx: discord.ApplicationContext, enabled: bool):
        if not is_admin(ctx):
            return await private(ctx, ADMIN_ONLY)
        await set_guild_var(ctx.guild.id, KEYS["enabled"], "true" if enabled else "false")
        await for_member(ctx, "Birthday feature **enabled**." if enabled else "Birthday feature **disabled**.")


def setup(bot: discord.Bot):
    bot.add_cog(Birthday(bot))
