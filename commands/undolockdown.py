import discord
from discord.ext import commands

from utils.lockdown import clear_lockdown, name_list, read_lockdown, restore_lockdown, save_lockdown


def summary(result, state) -> str:
    restored = result["restored"]
    roles = result["roles"]
    gone_roles = result["gone_roles"]
    missing = result["missing"]
    failed = result["failed"]

    channels = len({c.id for c in restored})
    lines = [
        "# Lockdown partly lifted" if failed else "# Lockdown lifted",
        f"Put back the permissions on **{channels}** {'channel' if channels == 1 else 'channels'}"
        + (f" for {', '.join(r.mention for r in roles)}" if roles else "")
        + ".",
    ]

    exceptions = list(
        dict.fromkeys(f"<#{t['exceptionId']}>" for t in state.get("targets") or [] if t.get("exceptionId"))
    )

    notes = []
    if exceptions:
        notes.append(f"{', '.join(exceptions)} was the exception.")
    if gone_roles:
        notes.append(
            f"{len(gone_roles)} locked {'role has' if len(gone_roles) == 1 else 'roles have'} been "
            "deleted since. Discord dropped their permissions with them, so there was nothing to put back."
        )
    if missing:
        notes.append(
            f"{len(missing)} {'channel no longer exists' if len(missing) == 1 else 'channels no longer exist'} "
            "and were skipped."
        )
    if failed:
        notes.append(
            f"**Still hidden**, I couldn't edit {len(failed)}: {name_list(failed)}\n"
            "  Give me **Manage Roles** there and run `/undolockdown` again; the rest stays as it is."
        )
    if notes:
        lines.extend(["", *(f"- {n}" for n in notes)])

    return "\n".join(lines)


class UndoLockdown(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(
        name="undolockdown",
        description="Lift the lockdown and put every channel permission back.",
        default_member_permissions=discord.Permissions(administrator=True),
        contexts={discord.InteractionContextType.guild},
    )
    async def undolockdown(self, ctx: discord.ApplicationContext):
        guild = ctx.guild

        # deferred first thing, for the same reason as /lockdown
        await ctx.defer(ephemeral=True)

        perms = ctx.interaction.permissions
        if not (perms and perms.administrator):
            return await ctx.edit(content="You need the **Administrator** permission to do that.")

        state = await read_lockdown(guild.id)
        if not state:
            return await ctx.edit(content="There's no lockdown running on this server.")

        reason = f"Lockdown lifted by {ctx.author}"
        result = await restore_lockdown(guild, state, reason)

        # keep the leftovers on record so a retry can finish the job; anything that
        # came back is dropped from it, so nothing gets restored twice
        if result["remaining"]:
            await save_lockdown(guild.id, result["remaining"])
        else:
            await clear_lockdown(guild.id)

        await ctx.edit(content=summary(result, state), allowed_mentions=discord.AllowedMentions.none())


def setup(bot: discord.Bot):
    bot.add_cog(UndoLockdown(bot))
