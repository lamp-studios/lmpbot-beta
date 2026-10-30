import asyncio
import re

import discord
from discord.ext import commands

from utils.db import delete_user_data
from utils.owner import is_bot_owner

# how long the Confirm / Cancel buttons stay live
CONFIRM_S = 60

# per-guild member search, capped so one slow guild can't hold the reply up
SEARCH_LIMIT = 100
SEARCH_TIMEOUT_S = 10

MENTION = re.compile(r"^<@!?(\d{17,20})>$")
SNOWFLAKE = re.compile(r"^\d{17,20}$")


def describe(target) -> str:
    """"@username (display name, id)" for reply text; `user` is None for an unknown id."""
    user = target["user"]
    if not user:
        return f"unknown user (`{target['id']}`)"
    return f"**@{user.name}** ({user.display_name}, `{target['id']}`)"


async def resolve_users(bot: discord.Bot, text: str):
    """
    Turn the `username` option into candidate users, as [{"id", "user"}].
    A mention or raw id is taken as is, so someone who has left every shared
    server can still be wiped. Anything else is matched exactly (ignoring case)
    against usernames in the user cache and in every guild the bot is in.
    """
    raw = text.strip()
    m = MENTION.match(raw)
    user_id = m.group(1) if m else (raw if SNOWFLAKE.match(raw) else None)
    if user_id:
        try:
            user = await bot.fetch_user(int(user_id))
        except Exception:
            user = None
        return [{"id": user_id, "user": user}]

    name = raw.removeprefix("@").lower()
    if not name:
        return []

    found = {}
    for user in bot.users:
        if user.name.lower() == name:
            found[user.id] = user

    # the cache only holds people the bot has seen lately, so ask every guild too
    async def search(guild: discord.Guild):
        return await asyncio.wait_for(guild.query_members(name, limit=SEARCH_LIMIT), SEARCH_TIMEOUT_S)

    results = await asyncio.gather(*(search(g) for g in bot.guilds), return_exceptions=True)
    for result in results:
        if isinstance(result, BaseException):
            continue
        for member in result:
            if member.name.lower() == name:
                found[member.id] = bot.get_user(member.id) or member

    return [{"id": str(uid), "user": user} for uid, user in found.items()]


def summary(target, results) -> str:
    lines = [f"Deleted stored data for {describe(target)}."]
    inactive = []

    for r in results:
        if r["status"] == "inactive":
            inactive.append(r["backend"])
        elif r["status"] == "failed":
            lines.append(f"- **{r['backend']}**: failed, {r['error'][:300]}")
        else:
            counts = ", ".join(f"{table} {'?' if n is None else n}" for table, n in r["counts"].items())
            lines.append(f"- **{r['backend']}**: {counts}")

    if inactive:
        lines.append(f"Not checked (not configured or not connected): {', '.join(inactive)}")
    if any(r["status"] == "failed" for r in results):
        lines.append("Run the command again once the failed backend is back to finish it off.")
    return "\n".join(lines)


class ConfirmView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=CONFIRM_S)
        self.author_id = author_id
        self.confirmed: bool | None = None
        self.click: discord.Interaction | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user is not None and interaction.user.id == self.author_id

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.confirmed = True
        self.click = interaction
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.confirmed = False
        self.click = interaction
        self.stop()


class DeleteData(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(
        name="delete_data",
        description="Bot owner only. Delete everything the bot has stored about one user.",
        default_member_permissions=discord.Permissions(administrator=True),
    )
    async def delete_data(
        self,
        ctx: discord.ApplicationContext,
        username: discord.Option(
            str,
            description="Their Discord username (not display name), a mention, or a user id.",
            required=True,
        ),
    ):
        if not await is_bot_owner(self.bot, ctx.author.id):
            await ctx.respond("Only the bot owner can delete user data.", ephemeral=True)
            return

        # searching every guild's members can take a few seconds
        await ctx.defer(ephemeral=True)

        matches = await resolve_users(self.bot, username)

        if not matches:
            await ctx.edit(
                content=(
                    f"Couldn't find a user with the username `{username}`. Check the spelling (it's the "
                    "username, not the display name), or pass their user id instead."
                )
            )
            return
        if len(matches) > 1:
            await ctx.edit(
                content=(
                    f"More than one user matches `{username}`, so nothing was deleted:\n"
                    + "\n".join(f"- {describe(m)}" for m in matches)
                    + "\nRun it again with the user id of the one you mean."
                )
            )
            return

        target = matches[0]
        view = ConfirmView(ctx.author.id)
        await ctx.edit(
            content=(
                f"Delete everything stored about {describe(target)}?\n"
                "That's their chat memory (and the bot's replies to them), remembered facts, and "
                "member settings like birthdays and verification, in every server and every "
                f"database. This can't be undone. The buttons expire in {CONFIRM_S} seconds."
            ),
            view=view,
        )

        timed_out = await view.wait()
        if timed_out or view.click is None:
            try:
                await ctx.edit(content="Timed out. Nothing was deleted.", view=None)
            except Exception:
                pass
            return

        click = view.click
        if not view.confirmed:
            await click.response.edit_message(content="Cancelled. Nothing was deleted.", view=None)
            return

        await click.response.edit_message(content=f"Deleting data for {describe(target)}...", view=None)
        results = await delete_user_data(target["id"])
        await ctx.edit(content=summary(target, results), view=None)


def setup(bot: discord.Bot):
    bot.add_cog(DeleteData(bot))
