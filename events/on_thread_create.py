import discord
from utils import db


def setup(bot: discord.Bot):
    @bot.event
    async def on_thread_create(thread: discord.Thread):
        if thread.guild is None or thread.parent is None:
            return

        forum_id = await db.get_guild_var(thread.guild.id, "forum_channel")
        if forum_id is None or str(thread.parent.id) != forum_id:
            return

        print(f"New forum post created: \"{thread.name}\" by {thread.owner_id} in #{thread.parent.name}")

        # add guild owner
        await thread.add_user(thread.guild.owner)

        # resolve staff role
        role_id = await db.get_guild_var(thread.guild.id, "staff_role")
        if role_id:
            role = thread.guild.get_role(int(role_id))
        else:
            role = discord.utils.get(thread.guild.roles, name="Admin")

        if role:
            for member in role.members:
                await thread.add_user(member)

        await thread.send("Staff members have been added!")
