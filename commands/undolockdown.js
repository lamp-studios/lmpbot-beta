import {
  SlashCommandBuilder,
  PermissionFlagsBits,
  InteractionContextType,
  MessageFlags,
} from "discord.js";
import {
  readLockdown,
  saveLockdown,
  clearLockdown,
  restoreLockdown,
  nameList,
} from "../utils/lockdown.js";

export default {
  data: new SlashCommandBuilder()
    .setName("undolockdown")
    .setDescription("Lift the lockdown and put every channel permission back.")
    .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
    .setContexts(InteractionContextType.Guild),

  async execute(interaction) {
    const guild = interaction.guild;

    // deferred first thing, for the same reason as /lockdown
    await interaction.deferReply({ flags: MessageFlags.Ephemeral });

    if (!interaction.memberPermissions?.has(PermissionFlagsBits.Administrator)) {
      return interaction.editReply("You need the **Administrator** permission to do that.");
    }

    const state = await readLockdown(guild.id);
    if (!state) {
      return interaction.editReply("There's no lockdown running on this server.");
    }

    await guild.channels.fetch().catch(() => null);

    const reason = `Lockdown lifted by ${interaction.user.tag}`;
    const result = await restoreLockdown(guild, state, reason);

    // keep the leftovers on record so a retry can finish the job; anything that
    // came back is dropped from it, so nothing gets restored twice
    if (result.remaining) await saveLockdown(guild.id, result.remaining);
    else await clearLockdown(guild.id);

    return interaction.editReply({
      content: summary(result, state),
      allowedMentions: { parse: [] },
    });
  },
};

function summary(result, state) {
  const { restored, roles, goneRoles, missing, failed } = result;

  const channels = new Set(restored.map((c) => c.id)).size;
  const lines = [
    failed.length ? "# Lockdown partly lifted" : "# Lockdown lifted",
    `Put back the permissions on **${channels}** ${channels === 1 ? "channel" : "channels"}` +
      (roles.length ? ` for ${roles.join(", ")}` : "") +
      ".",
  ];

  const exceptions = (state.targets ?? [])
    .filter((t) => t.exceptionId)
    .map((t) => `<#${t.exceptionId}>`);

  const notes = [];
  if (exceptions.length) {
    notes.push(`${[...new Set(exceptions)].join(", ")} was the exception.`);
  }
  if (goneRoles.length) {
    notes.push(
      `${goneRoles.length} locked ${goneRoles.length === 1 ? "role has" : "roles have"} been ` +
        "deleted since. Discord dropped their permissions with them, so there was nothing to put back."
    );
  }
  if (missing.length) {
    notes.push(
      `${missing.length} ${
        missing.length === 1 ? "channel no longer exists" : "channels no longer exist"
      } and were skipped.`
    );
  }
  if (failed.length) {
    notes.push(
      `**Still hidden**, I couldn't edit ${failed.length}: ${nameList(failed)}\n` +
        "  Give me **Manage Roles** there and run `/undolockdown` again; the rest stays as it is."
    );
  }
  if (notes.length) lines.push("", ...notes.map((n) => `- ${n}`));

  return lines.join("\n");
}
