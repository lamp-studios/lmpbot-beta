import discord
from discord.ext import commands

from utils.birthdays import snowflake
from utils.db import get_guild_var


class ThreadCreate(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        if not thread.guild or not thread.parent:
            return
        guild = thread.guild

        forum_id = await get_guild_var(guild.id, "forum_channel")
        if not forum_id or str(thread.parent.id) != forum_id:
            return

        print(f'New forum post created: "{thread.name}" by {thread.owner_id} in #{thread.parent.name}')

        # add guild owner
        owner = guild.owner or await guild.fetch_member(guild.owner_id)
        if owner:
            await thread.add_user(owner)

        # resolve staff role
        role_id = snowflake(await get_guild_var(guild.id, "staff_role"))
        role = guild.get_role(role_id) if role_id else discord.utils.get(guild.roles, name="Admin")

        if role:
            if not guild.chunked:
                await guild.chunk()
            for member in list(role.members):
                await thread.add_user(member)

        await thread.send("Staff members have been added!")


def setup(bot: discord.Bot):
    bot.add_cog(ThreadCreate(bot))
