import { Events, MessageFlags } from "discord.js";

export default {
  name: Events.InteractionCreate,

  async execute(interaction) {
    if (interaction.isAutocomplete()) {
      const command = interaction.client.commands.get(interaction.commandName);
      if (!command?.autocomplete) return;

      try {
        await command.autocomplete(interaction);
      } catch (err) {
        console.error(`Autocomplete failed for /${interaction.commandName}:`, err);
      }
      return;
    }

    if (interaction.isChatInputCommand()) {
      const command = interaction.client.commands.get(interaction.commandName);
      if (!command) return;

      try {
        await command.execute(interaction);
      } catch (err) {
        console.error(`Error running /${interaction.commandName}:`, err);
        const payload = {
          content: "Something went wrong running that command.",
          flags: MessageFlags.Ephemeral,
        };
        if (interaction.deferred || interaction.replied) {
          await interaction.followUp(payload).catch(() => {});
        } else {
          await interaction.reply(payload).catch(() => {});
        }
      }
      return;
    }

    if (interaction.isButton() && interaction.customId === "learnmore") {
      await interaction.reply({
        content:
          "To automatically ban/kick bots, since most popular discord bots don't " +
          "have that feature, *yet*. We had to make our own for our server.",
        flags: MessageFlags.Ephemeral,
      });
    }
  },
};
