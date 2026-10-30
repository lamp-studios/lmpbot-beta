async def register_commands(bot) -> int:
    """
    Register/update all loaded slash commands globally, replacing whatever was
    registered before (the old `.up` behaviour). Returns how many were sent.
    """
    commands = bot.pending_application_commands
    await bot.sync_commands(commands=commands, method="bulk", force=True)
    return len(commands)
