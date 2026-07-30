import {
  SlashCommandBuilder,
  PermissionFlagsBits,
  InteractionContextType,
  ChannelType,
  MessageFlags,
} from "discord.js";
import {
  applyLockdown,
  readLockdown,
  saveLockdown,
  lockedRoleIds,
  manageable,
  nameList,
} from "../utils/lockdown.js";

// everything except categories and threads, which can't sensibly be the one
// channel members are left with
const EXCEPTION_TYPES = [
  ChannelType.GuildText,
  ChannelType.GuildAnnouncement,
  ChannelType.GuildForum,
  ChannelType.GuildMedia,
  ChannelType.GuildVoice,
  ChannelType.GuildStageVoice,
];

export default {
  data: new SlashCommandBuilder()
    .setName("lockdown")
    .setDescription("Hide every channel from a role, apart from one.")
    .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
    .setContexts(InteractionContextType.Guild)
    .addChannelOption((o) =>
      o
        .setName("channel-exception")
        .setDescription("The one channel the role keeps seeing. Leave it out to hide everything.")
        .addChannelTypes(...EXCEPTION_TYPES)
        .setRequired(false)
    )
    .addRoleOption((o) =>
      o
        .setName("role")
        .setDescription("Role to hide the channels from. Defaults to @everyone.")
        .setRequired(false)
    ),

  async execute(interaction) {
    const guild = interaction.guild;

    // deferred first thing: the checks below read the database, and the edits
    // on a big server run well past the three seconds a first reply gets
    await interaction.deferReply({ flags: MessageFlags.Ephemeral });

    // the default permission can be re-pointed at another role in Server
    // Settings, so the check is made again here for something this destructive
    if (!interaction.memberPermissions?.has(PermissionFlagsBits.Administrator)) {
      return interaction.editReply("You need the **Administrator** permission to do that.");
    }

    const me = guild.members.me ?? (await guild.members.fetchMe());
    if (!me.permissions.has(PermissionFlagsBits.ManageRoles)) {
      return interaction.editReply(
        "I need the **Manage Roles** permission to change channel permissions."
      );
    }

    const role = interaction.options.getRole("role");
    const target = role ?? guild.roles.everyone;

    // Locking a role twice would save the locked-down permissions as the ones to
    // restore, so only a role that isn't already held down can be added.
    const previous = await readLockdown(guild.id);
    if (previous && lockedRoleIds(previous).includes(target.id)) {
      return interaction.editReply({
        content:
          `${target} is **already locked down** on this server. Run \`/undolockdown\` first, ` +
          "otherwise the permissions from before the lockdown would be lost.",
        allowedMentions: { parse: [] },
      });
    }

    await guild.channels.fetch().catch(() => null);

    const exception = interaction.options.getChannel("channel-exception");
    if (exception && !manageable(exception, me)) {
      return interaction.editReply(
        `I can't edit permissions in ${exception}, so members would be left with nowhere ` +
          "to go. Give me **Manage Roles** there and run this again."
      );
    }

    const reason = `Lockdown of ${target.name} by ${interaction.user.tag}`;
    const result = await applyLockdown(guild, {
      role,
      exception,
      user: interaction.user,
      reason,
      previous,
    });

    if (!result.state) {
      return interaction.editReply({
        content: result.skipped.length
          ? "Nothing changed — I can't edit permissions in any of this server's channels."
          : `Nothing changed — every channel is already hidden from ${target}.`,
        allowedMentions: { parse: [] },
      });
    }

    await saveLockdown(guild.id, result.state);
    return interaction.editReply({
      content: summary(result, exception, previous),
      allowedMentions: { parse: [] },
    });
  },
};

function summary(result, exception, previous) {
  const { target, hidden, alreadyHidden, skipped, failed, exceptionWasHidden } = result;

  const lines = [
    "# Lockdown active",
    `Hid **${hidden.length}** ${hidden.length === 1 ? "channel" : "channels"} from ${target}.` +
      (exception ? ` ${exception} is the only one it can still see.` : ""),
  ];

  if (target.permissions.has(PermissionFlagsBits.Administrator)) {
    lines.push(
      `\n⚠️ ${target} has **Administrator**, which ignores channel permissions — its ` +
        "members can still see everything."
    );
  }
  if (exceptionWasHidden) {
    lines.push(
      `\n⚠️ ${exception} was hidden from ${target} before this, and is now visible to it. ` +
        "`/undolockdown` hides it again."
    );
  }
  const notes = [];
  if (previous) {
    const others = previous.targets.map((t) => `<@&${t.roleId}>`).join(", ");
    notes.push(`Added to the lockdown already running for ${others}.`);
  }
  if (alreadyHidden) {
    notes.push(
      `${alreadyHidden} ${alreadyHidden === 1 ? "channel was" : "channels were"} already ` +
        "hidden from it and were left alone."
    );
  }
  if (skipped.length) {
    notes.push(`Couldn't touch ${skipped.length} (no **Manage Roles** there): ${nameList(skipped)}`);
  }
  if (failed.length) {
    notes.push(`**Failed** on ${failed.length}: ${nameList(failed)}`);
  }
  if (notes.length) lines.push("", ...notes.map((n) => `- ${n}`));

  lines.push("", "Run `/undolockdown` to put every permission back exactly as it was.");
  return lines.join("\n");
}
