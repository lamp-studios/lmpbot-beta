import discord
from discord.ext import commands

from config import config

P = config.prefix

# Single source for both the overview list and the per-command detail view.
# `perm` is what the bot actually enforces, not just the default permission.
COMMANDS = [
    {
        "name": "help",
        "type": "slash",
        "usage": "/help [command]",
        "perm": "Everyone",
        "short": "Shows this message.",
        "long": (
            "Lists every command. Pass a command name for details on just that one, "
            "e.g. `/help birthday`."
        ),
    },
    {
        "name": "birthday",
        "type": "slash",
        "usage": "/birthday set|list|upcoming|visibility|settings|enable|disable",
        "perm": "Everyone, settings are Admin",
        "short": "Birthday announcements and roles.",
        "long": (
            "- `/birthday set <date>` (Everyone) saves your birthday as day/month, e.g. `30/01`.\n"
            "- `/birthday list` (Everyone) shows every birthday on the server in calendar "
            "order, grouped by month.\n"
            "- `/birthday upcoming [days]` (Everyone) shows just the ones coming up, soonest "
            "first. Defaults to the next 30 days.\n"
            "- `/birthday visibility [mode]` (Everyone) picks whether your `/birthday` replies "
            "are only visible to you or posted in the channel. Replies are private until you "
            "change it. Run it with no option to see what you're on.\n"
            "- `/birthday settings` (Admin) sets the birthday role, announcement channel, "
            "custom message (`{user}`, `{mention}`, `{name}`), ping role, and the channel "
            "members have to run `/birthday set` in. Run it with no options to see the "
            "current settings.\n"
            "- `/birthday enable` and `/birthday disable` (Admin) turn the feature on or off. "
            "It starts off.\n\n"
            "Announcements go out once a day, from 08:00 bot time. The birthday role is "
            "taken back off the next day."
        ),
    },
    {
        "name": "lockdown",
        "type": "slash",
        "usage": "/lockdown [channel-exception] [role]",
        "perm": "Admin",
        "short": "Hides every channel from a role, apart from one.",
        "long": (
            "Denies **View Channel** in every channel on the server, so the role can't see "
            "anything.\n"
            "- `channel-exception` is the one channel that stays visible. Leave it out and the "
            "whole server goes dark.\n"
            "- `role` is who gets shut out, and defaults to `@everyone`. Point it at your "
            "member role if that role is what grants View Channel, since a deny on `@everyone` "
            "does nothing to people who have it.\n"
            "Channels the role already couldn't see are left alone, and so is every other "
            "permission; only the View Channel bit is touched.\n"
            "What each channel looked like beforehand is saved, so `/undolockdown` puts it all "
            "back exactly as it was. Running it again for a *different* role adds that role to "
            "the same lockdown; a role that's already locked needs `/undolockdown` first."
        ),
    },
    {
        "name": "undolockdown",
        "type": "slash",
        "usage": "/undolockdown",
        "perm": "Admin",
        "short": "Lifts the lockdown and restores every channel.",
        "long": (
            "Restores the View Channel permission on every channel `/lockdown` changed, for "
            "every role it locked, back to whatever it was before: allowed, denied or unset. "
            "Channels that have been deleted since are skipped, and any the bot still can't "
            "edit stay on record so running the command again finishes them off."
        ),
    },
    {
        "name": "members",
        "type": "slash",
        "usage": "/members",
        "perm": "Everyone",
        "short": "Lists everyone who has verified.",
        "long": (
            f"Lists every member who has run `{P}verify` on this server. The reply is "
            "only shown to you and nobody gets pinged."
        ),
    },
    {
        "name": "set_verification_role",
        "type": "slash",
        "usage": "/set_verification_role [role]",
        "perm": "Admin",
        "short": f"Sets the role given on `{P}verify`, and enables verification.",
        "long": (
            f"Sets the role a member gets when they run `{P}verify`, and turns "
            "verification on.\n"
            "Run it with no role to remove the role and turn verification back off."
        ),
    },
    {
        "name": "set_bot_channel",
        "type": "slash",
        "usage": "/set_bot_channel [channel] [log_channel]",
        "perm": "Admin",
        "short": "Sets a spambot trap channel.",
        "long": (
            "Anyone who posts in the `channel` gets their message deleted, gets a DM, and is "
            "banned then immediately unbanned, which clears their recent messages and kicks "
            "them off the server. Meant for a bait channel that real members are told not to "
            "post in.\n"
            "`log_channel` is optional and gets a note naming everyone the trap catches.\n"
            "Either option can be set on its own. Run the command with neither to turn the "
            "trap and its logging back off."
        ),
    },
    {
        "name": "set_chatbot_channel",
        "type": "slash",
        "usage": "/set_chatbot_channel <channel>",
        "perm": "Admin",
        "short": "Sets a channel where the chatbot replies.",
        "long": (
            "Every message in this channel gets an AI reply. The bot keeps a per-user "
            "history of the channel and remembers facts about you, like your name or what "
            "you're building, so it carries context between messages.\n"
            "Post an image and the AI looks at it, as long as the model can see images "
            "(Gemini, GPT-4o and Ollama vision models like `llava` can; plain text models "
            "can't). Up to 4 images a message, 5 MB each.\n"
            "Mentions are handed to the AI as `@username (display name, id)` so it knows who "
            "everyone is, and it can mention people back. It can only ping you and anyone "
            "you mentioned yourself.\n"
            "Which AI answers is set with `/setchatbotai`, and is Gemini until you change it."
        ),
    },
    {
        "name": "setchatbotai",
        "type": "slash",
        "usage": "/setchatbotai [provider] [model] [scope]",
        "perm": "Owner",
        "short": "Picks which AI answers in the chatbot channel.",
        "long": (
            "Sets the chatbot AI. Only the bot owner can run it, including anyone on the "
            "bot's Discord developer team. Run it with no options to see what you're on.\n"
            "- `provider:gemini` uses Google's Gemini, and needs `GEMINI_API_KEY` set on the "
            "bot. `model` is optional and defaults to `gemini-2.5-flash`.\n"
            "- `provider:openai` needs `OPENAI_API_KEY`. `model` is required and is checked "
            "against what that key can actually use, e.g. `gpt-4o-mini`. Point "
            "`OPENAI_BASE_URL` at any OpenAI-compatible endpoint to use that instead.\n"
            "- `provider:ollama` uses a model running on the bot's own Ollama server, so "
            "nothing leaves the host and no API key is needed. `model` is required, e.g. "
            "`llama3` or `qwen2.5:7b`, anything from <https://ollama.com/library>. If that "
            "model isn't installed yet the bot downloads it for you and reports progress. "
            "Ollama itself has to be running; the bot uses `http://127.0.0.1:11434` unless "
            "`OLLAMA_HOST` says otherwise.\n\n"
            "`scope` decides how far the change reaches:\n"
            "- `server` (the default) changes this server only, and overrides the global one.\n"
            "- `global` sets the default every server without its own setting falls back to.\n"
            "- `clear` removes this server's setting so it follows the global default again.\n\n"
            "The `model` option autocompletes with the models the provider offers. Nothing is "
            "saved until the model is ready, so a failed download or a bad model name leaves "
            "the current AI alone."
        ),
    },
    {
        "name": "delete_data",
        "type": "slash",
        "usage": "/delete_data <username>",
        "perm": "Owner",
        "short": "Deletes everything the bot has stored about one user.",
        "long": (
            "Wipes a user's chat memory (their messages and the bot's replies to them), the "
            "facts the chatbot remembered about them, and their member settings such as "
            "birthday and verification, in every server and every database. Server settings "
            "are left alone. Only the bot owner can run it.\n"
            "`username` is their Discord username, not the display name. A mention or a raw "
            "user id works too, which is how to reach someone who has left every server the "
            "bot is in. If more than one user matches, they're listed and nothing is deleted.\n"
            "You get a Confirm / Cancel prompt first, which expires after 60 seconds, then a "
            "count of what was removed from each database."
        ),
    },
    {
        "name": "set_forum_channel",
        "type": "slash",
        "usage": "/set_forum_channel <channel> [role]",
        "perm": "Admin",
        "short": "Auto-adds staff to new posts in a forum channel.",
        "long": (
            "When a post is created in this forum channel, the bot adds the server owner and "
            "everyone with the staff role to the thread. If no role is given it looks for a "
            "role named `Admin`."
        ),
    },
    {
        "name": "set_news_channel",
        "type": "slash",
        "usage": "/set_news_channel <channel>",
        "perm": "Admin",
        "short": "Sets where bot news is posted.",
        "long": "Bot updates and announcements sent by the bot owner land in this channel.",
    },
    {
        "name": "welcome",
        "type": "slash",
        "usage": "/welcome <channel> <mentions> [welcome_message]",
        "perm": "Owner",
        "short": "Sends a welcome message for every member. Currently disabled.",
        "long": (
            "Sends a welcome message for every member of the server into one channel.\n"
            "This is disabled for now because of Top.gg's rules on mass mentions."
        ),
    },
    {
        "name": "verify",
        "type": "prefix",
        "usage": f"{P}verify",
        "perm": "Everyone",
        "short": "Verifies you and gives you the verification role.",
        "long": (
            "Marks you as verified and gives you the role set with "
            "`/set_verification_role`. An admin has to set that role before this works."
        ),
    },
    {
        "name": "ping",
        "type": "prefix",
        "usage": f"{P}ping",
        "perm": "Everyone",
        "short": "Shows the bot's ping.",
        "long": "Replies with the bot's current gateway latency in milliseconds.",
    },
    {
        "name": "info",
        "type": "prefix",
        "usage": f"{P}info",
        "perm": "Everyone",
        "short": "Shows bot stats and info.",
        "long": "Shows the bot's ping, how long it has been up, and the host OS.",
    },
    {
        "name": "up",
        "type": "prefix",
        "usage": f"{P}up",
        "perm": "Owner",
        "short": "Re-registers all slash commands.",
        "long": (
            "Pushes the current slash commands to Discord. Run this after any command is "
            "added or changed."
        ),
    },
    {
        "name": "exe",
        "type": "prefix",
        "usage": f"{P}exe <code>",
        "perm": "Owner",
        "short": "Runs Python through the bot.",
        "long": (
            "Runs Python with `bot`, `client`, `message` and `discord` in scope, and sends "
            "back whatever it returns. A single expression is sent back as-is; longer code "
            "runs as an async function body, so `await` works and `return` sends a value."
        ),
    },
    {
        "name": "send_new",
        "type": "prefix",
        "usage": f"{P}send_new <message>",
        "perm": "Owner",
        "short": "Broadcasts bot news to every server.",
        "long": (
            "Sends the message to the news channel of every server that has set one with "
            "`/set_news_channel`."
        ),
    },
]


def find(query: str):
    words = str(query).strip().lower()
    if words[:1] in ("/", "."):
        words = words[1:]
    key = words.split()[0] if words.split() else ""
    return next((c for c in COMMANDS if c["name"] == key), None)


def overview() -> str:
    def line(c):
        perm = "" if c["perm"] == "Everyone" else f" *({c['perm']})*"
        return f"- `{c['usage']}`{perm}\n  {c['short']}"

    return "\n".join(
        [
            "# Help",
            "Use `/help <command>` for more on any one of these.",
            "",
            "## Slash commands",
            *(line(c) for c in COMMANDS if c["type"] == "slash"),
            "",
            f"## Prefix commands (`{P}`)",
            *(line(c) for c in COMMANDS if c["type"] == "prefix"),
        ]
    )


def detail(cmd) -> str:
    return "\n".join(
        [
            f"# {'/' if cmd['type'] == 'slash' else P}{cmd['name']}",
            f"`{cmd['usage']}`",
            f"Who can use it: **{cmd['perm']}**",
            "",
            cmd["long"],
        ]
    )


async def autocomplete_command(ctx: discord.AutocompleteContext):
    typed = (ctx.value or "").lower()
    if typed[:1] in ("/", "."):
        typed = typed[1:]
    matches = [c for c in COMMANDS if typed in c["name"]][:25]
    return [discord.OptionChoice(name=c["usage"], value=c["name"]) for c in matches]


class Help(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(
        name="help",
        description="See all commands and what they do (includes prefix commands).",
    )
    async def help(
        self,
        ctx: discord.ApplicationContext,
        command: discord.Option(
            str,
            description="Command to show help for.",
            required=False,
            default=None,
            autocomplete=autocomplete_command,
        ),
    ):
        if not command:
            await ctx.respond(overview(), ephemeral=True)
            return

        cmd = find(command)
        text = detail(cmd) if cmd else f"There's no command called `{command}`. Run `/help` to see them all."
        await ctx.respond(text, ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(Help(bot))
