import { SlashCommandBuilder, MessageFlags } from "discord.js";
import { config } from "../config.js";

const P = config.prefix;

// Single source for both the overview list and the per-command detail view.
// `perm` is what the bot actually enforces, not just the default permission.
const COMMANDS = [
  {
    name: "help",
    type: "slash",
    usage: "/help [command]",
    perm: "Everyone",
    short: "Shows this message.",
    long:
      "Lists every command. Pass a command name for details on just that one, " +
      "e.g. `/help birthday`.",
  },
  {
    name: "birthday",
    type: "slash",
    usage: "/birthday set|settings|enable|disable",
    perm: "Everyone, settings are Admin",
    short: "Birthday announcements and roles.",
    long:
      "- `/birthday set <date>` (Everyone) saves your birthday as day/month, e.g. `30/01`.\n" +
      "- `/birthday settings` (Admin) sets the birthday role, announcement channel, " +
      "custom message (`{user}`, `{mention}`, `{name}`), ping role, and the channel " +
      "members have to run `/birthday set` in. Run it with no options to see the " +
      "current settings.\n" +
      "- `/birthday enable` and `/birthday disable` (Admin) turn the feature on or off. " +
      "It starts off.\n\n" +
      "Announcements go out once a day, from 08:00 bot time. The birthday role is " +
      "taken back off the next day.",
  },
  {
    name: "members",
    type: "slash",
    usage: "/members",
    perm: "Everyone",
    short: "Lists everyone who has verified.",
    long:
      `Lists every member who has run \`${P}verify\` on this server. The reply is ` +
      "only shown to you and nobody gets pinged.",
  },
  {
    name: "set_verification_role",
    type: "slash",
    usage: "/set_verification_role [role]",
    perm: "Admin",
    short: `Sets the role given on \`${P}verify\`, and enables verification.`,
    long:
      `Sets the role a member gets when they run \`${P}verify\`, and turns ` +
      "verification on.\n" +
      "Run it with no role to remove the role and turn verification back off.",
  },
  {
    name: "set_bot_channel",
    type: "slash",
    usage: "/set_bot_channel <channel>",
    perm: "Admin",
    short: "Sets a spambot trap channel.",
    long:
      "Anyone who posts in this channel gets their message deleted, gets a DM, and is " +
      "banned then immediately unbanned, which clears their recent messages and kicks " +
      "them off the server. Meant for a bait channel that real members are told not to " +
      "post in.",
  },
  {
    name: "set_chatbot_channel",
    type: "slash",
    usage: "/set_chatbot_channel <channel>",
    perm: "Admin",
    short: "Sets a channel where the Gemini chatbot replies.",
    long:
      "Every message in this channel gets a Gemini reply. The bot keeps a per-user " +
      "history of the channel and remembers facts about you, like your name or what " +
      "you're building, so it carries context between messages.",
  },
  {
    name: "set_forum_channel",
    type: "slash",
    usage: "/set_forum_channel <channel> [role]",
    perm: "Admin",
    short: "Auto-adds staff to new posts in a forum channel.",
    long:
      "When a post is created in this forum channel, the bot adds the server owner and " +
      "everyone with the staff role to the thread. If no role is given it looks for a " +
      "role named `Admin`.",
  },
  {
    name: "set_news_channel",
    type: "slash",
    usage: "/set_news_channel <channel>",
    perm: "Admin",
    short: "Sets where bot news is posted.",
    long:
      "Bot updates and announcements sent by the bot owner land in this channel.",
  },
  {
    name: "welcome",
    type: "slash",
    usage: "/welcome <channel> <mentions> [welcome_message]",
    perm: "Owner",
    short: "Sends a welcome message for every member. Currently disabled.",
    long:
      "Sends a welcome message for every member of the server into one channel.\n" +
      "This is disabled for now because of Top.gg's rules on mass mentions.",
  },
  {
    name: "verify",
    type: "prefix",
    usage: `${P}verify`,
    perm: "Everyone",
    short: "Verifies you and gives you the verification role.",
    long:
      "Marks you as verified and gives you the role set with " +
      "`/set_verification_role`. An admin has to set that role before this works.",
  },
  {
    name: "ping",
    type: "prefix",
    usage: `${P}ping`,
    perm: "Everyone",
    short: "Shows the bot's ping.",
    long: "Replies with the bot's current gateway latency in milliseconds.",
  },
  {
    name: "info",
    type: "prefix",
    usage: `${P}info`,
    perm: "Everyone",
    short: "Shows bot stats and info.",
    long: "Shows the bot's ping, how long it has been up, and the host OS.",
  },
  {
    name: "up",
    type: "prefix",
    usage: `${P}up`,
    perm: "Owner",
    short: "Re-registers all slash commands.",
    long:
      "Pushes the current slash commands to Discord. Run this after any command is " +
      "added or changed.",
  },
  {
    name: "exe",
    type: "prefix",
    usage: `${P}exe <code>`,
    perm: "Owner",
    short: "Runs JavaScript through the bot.",
    long:
      "Evaluates JavaScript with `bot`, `client`, `message` and `discord` in scope, " +
      "and sends back whatever it returns.",
  },
  {
    name: "send_new",
    type: "prefix",
    usage: `${P}send_new <message>`,
    perm: "Owner",
    short: "Broadcasts bot news to every server.",
    long:
      "Sends the message to the news channel of every server that has set one with " +
      "`/set_news_channel`.",
  },
];

function find(query) {
  const key = String(query).trim().toLowerCase().replace(/^[/.]/, "").split(/\s+/)[0];
  return COMMANDS.find((c) => c.name === key) ?? null;
}

function overview() {
  const line = (c) =>
    `- \`${c.usage}\`${c.perm === "Everyone" ? "" : ` *(${c.perm})*`}\n  ${c.short}`;

  return [
    "# Help",
    `Use \`/help <command>\` for more on any one of these.`,
    "",
    "## Slash commands",
    ...COMMANDS.filter((c) => c.type === "slash").map(line),
    "",
    `## Prefix commands (\`${P}\`)`,
    ...COMMANDS.filter((c) => c.type === "prefix").map(line),
  ].join("\n");
}

function detail(cmd) {
  return [
    `# ${cmd.type === "slash" ? "/" : P}${cmd.name}`,
    `\`${cmd.usage}\``,
    `Who can use it: **${cmd.perm}**`,
    "",
    cmd.long,
  ].join("\n");
}

export default {
  data: new SlashCommandBuilder()
    .setName("help")
    .setDescription("See all commands and what they do (includes prefix commands).")
    .addStringOption((o) =>
      o
        .setName("command")
        .setDescription("Command to show help for.")
        .setRequired(false)
        .setAutocomplete(true)
    ),

  async autocomplete(interaction) {
    const typed = interaction.options.getFocused().toLowerCase().replace(/^[/.]/, "");
    const matches = COMMANDS.filter((c) => c.name.includes(typed)).slice(0, 25);
    await interaction.respond(
      matches.map((c) => ({ name: c.usage, value: c.name }))
    );
  },

  async execute(interaction) {
    const query = interaction.options.getString("command");

    if (!query) {
      await interaction.reply({ content: overview(), flags: MessageFlags.Ephemeral });
      return;
    }

    const cmd = find(query);
    const text = cmd
      ? detail(cmd)
      : `There's no command called \`${query}\`. Run \`/help\` to see them all.`;

    await interaction.reply({ content: text, flags: MessageFlags.Ephemeral });
  },
};
