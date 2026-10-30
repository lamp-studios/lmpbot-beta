import discord
from discord.ext import commands

from utils.lockdown import (
    apply_lockdown,
    locked_role_ids,
    manageable,
    name_list,
    read_lockdown,
    save_lockdown,
)

# everything except categories and threads, which can't sensibly be the one
# channel members are left with
EXCEPTION_TYPES = [
    discord.ChannelType.text,
    discord.ChannelType.news,
    discord.ChannelType.forum,
    discord.ChannelType.media,
    discord.ChannelType.voice,
    discord.ChannelType.stage_voice,
]

NO_MENTIONS = discord.AllowedMentions.none()


def summary(result, exception, previous) -> str:
    target = result["target"]
    hidden = result["hidden"]
    already_hidden = result["already_hidden"]
    skipped = result["skipped"]
    failed = result["failed"]

    lines = [
        "# Lockdown active",
        f"Hid **{len(hidden)}** {'channel' if len(hidden) == 1 else 'channels'} from {target.mention}."
        + (f" {exception.mention} is the only one it can still see." if exception else ""),
    ]

    if target.permissions.administrator:
        lines.append(
            f"\n⚠️ {target.mention} has **Administrator**, which ignores channel permissions, so its "
            "members can still see everything."
        )
    if result["exception_was_hidden"]:
        lines.append(
            f"\n⚠️ {exception.mention} was hidden from {target.mention} before this, and is now visible to it. "
            "`/undolockdown` hides it again."
        )

    notes = []
    if previous:
        others = ", ".join(f"<@&{t['roleId']}>" for t in previous["targets"])
        notes.append(f"Added to the lockdown already running for {others}.")
    if already_hidden:
        notes.append(
            f"{already_hidden} {'channel was' if already_hidden == 1 else 'channels were'} already "
            "hidden from it and were left alone."
        )
    if skipped:
        notes.append(f"Couldn't touch {len(skipped)} (no **Manage Roles** there): {name_list(skipped)}")
    if failed:
        notes.append(f"**Failed** on {len(failed)}: {name_list(failed)}")
    if notes:
        lines.extend(["", *(f"- {n}" for n in notes)])

    lines.extend(["", "Run `/undolockdown` to put every permission back exactly as it was."])
    return "\n".join(lines)


class Lockdown(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(
        name="lockdown",
        description="Hide every channel from a role, apart from one.",
        default_member_permissions=discord.Permissions(administrator=True),
        contexts={discord.InteractionContextType.guild},
    )
    async def lockdown(
        self,
        ctx: discord.ApplicationContext,
        channel_exception: discord.Option(
            discord.abc.GuildChannel,
            name="channel-exception",
            description="The one channel the role keeps seeing. Leave it out to hide everything.",
            channel_types=EXCEPTION_TYPES,
            required=False,
            default=None,
        ),
        role: discord.Option(
            discord.Role,
            description="Role to hide the channels from. Defaults to @everyone.",
            required=False,
            default=None,
        ),
    ):
        guild = ctx.guild

        # deferred first thing: the checks below read the database, and the edits
        # on a big server run well past the three seconds a first reply gets
        await ctx.defer(ephemeral=True)

        # the default permission can be re-pointed at another role in Server
        # Settings, so the check is made again here for something this destructive
        perms = ctx.interaction.permissions
        if not (perms and perms.administrator):
            return await ctx.edit(content="You need the **Administrator** permission to do that.")

        me = guild.me
        if not me.guild_permissions.manage_roles:
            return await ctx.edit(content="I need the **Manage Roles** permission to change channel permissions.")

        target = role or guild.default_role

        # Locking a role twice would save the locked-down permissions as the ones to
        # restore, so only a role that isn't already held down can be added.
        previous = await read_lockdown(guild.id)
        if previous and str(target.id) in locked_role_ids(previous):
            return await ctx.edit(
                content=(
                    f"{target.mention} is **already locked down** on this server. Run `/undolockdown` first, "
                    "otherwise the permissions from before the lockdown would be lost."
                ),
                allowed_mentions=NO_MENTIONS,
            )

        # the option resolves to a partial channel; act on the cached one
        exception = guild.get_channel(channel_exception.id) if channel_exception else None
        if channel_exception and (exception is None or not manageable(exception, me)):
            return await ctx.edit(
                content=(
                    f"I can't edit permissions in <#{channel_exception.id}>, so members would be left with nowhere "
                    "to go. Give me **Manage Roles** there and run this again."
                )
            )

        reason = f"Lockdown of {target.name} by {ctx.author}"
        result = await apply_lockdown(
            guild,
            role=role,
            exception=exception,
            user=ctx.author,
            reason=reason,
            previous=previous,
        )

        if not result["state"]:
            return await ctx.edit(
                content=(
                    "Nothing changed. I can't edit permissions in any of this server's channels."
                    if result["skipped"]
                    else f"Nothing changed, every channel is already hidden from {target.mention}."
                ),
                allowed_mentions=NO_MENTIONS,
            )

        await save_lockdown(guild.id, result["state"])
        await ctx.edit(content=summary(result, exception, previous), allowed_mentions=NO_MENTIONS)


def setup(bot: discord.Bot):
    bot.add_cog(Lockdown(bot))
