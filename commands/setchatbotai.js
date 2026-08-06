import {
  SlashCommandBuilder,
  PermissionFlagsBits,
  MessageFlags,
} from "discord.js";
import { config } from "../config.js";
import * as ai from "../utils/ai.js";
import * as gemini from "../utils/gemini.js";
import * as openai from "../utils/openai.js";
import * as ollama from "../utils/ollama.js";
import { isBotOwner } from "../utils/owner.js";

// how often the download progress message is edited (Discord rate limits edits)
const PROGRESS_EDIT_MS = 6000;

// model ids the chat endpoint can't use, kept out of the autocomplete list
const NON_CHAT = /embed|whisper|tts|audio|image|dall-e|moderation|transcribe|realtime|sora/i;

function formatBytes(n) {
  if (!Number.isFinite(n) || n <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(Math.floor(Math.log(n) / Math.log(1024)), units.length - 1);
  return `${(n / 1024 ** i).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function progressLine(model, evt) {
  const status = evt?.status ?? "working";
  if (evt?.total > 0 && evt?.completed >= 0) {
    const pct = Math.min(100, Math.floor((evt.completed / evt.total) * 100));
    return (
      `Installing \`${model}\`: ${status} ${pct}% ` +
      `(${formatBytes(evt.completed)} / ${formatBytes(evt.total)})`
    );
  }
  return `Installing \`${model}\`: ${status}...`;
}

const ollamaHost = () => config.ollamaHost || "http://127.0.0.1:11434";

/** "for this server" / "as the global default", for reply text. */
function scopeText(scope) {
  return scope === "global"
    ? "as the global default for every server"
    : "for this server";
}

/**
 * Edit the deferred reply, falling back to a channel message once the
 * interaction token has expired. A big model pull can outlast the 15 minute
 * window, and the result still needs to reach whoever ran the command.
 */
async function report(interaction, content) {
  try {
    await interaction.editReply({ content });
  } catch {
    await interaction.channel
      ?.send({
        content: `<@${interaction.user.id}> ${content}`,
        allowedMentions: { users: [interaction.user.id] },
      })
      .catch(() => {});
  }
}

/** Warn about the things that stop a provider replying, if any apply. */
async function healthNote(provider) {
  if (provider === "gemini" && !config.geminiApiKey) {
    return "Heads up: `GEMINI_API_KEY` isn't set on the bot, so replies will fail.";
  }
  if (provider === "openai" && !openai.hasKey()) {
    return "Heads up: `OPENAI_API_KEY` isn't set on the bot, so replies will fail.";
  }
  if (provider === "ollama" && !(await ollama.reachable())) {
    return `Heads up: the Ollama server at \`${ollamaHost()}\` isn't reachable, so replies will fail.`;
  }
  return null;
}

async function showCurrent(interaction) {
  const current = await ai.getSettings(interaction.guild?.id);
  const global = await ai.getGlobalSettings();

  const source =
    current.scope === "server"
      ? "set for this server"
      : current.scope === "global"
        ? "the global default"
        : "the built-in default";

  const lines = [
    `This server is on **${ai.label(current.provider, current.model)}** (${source}).`,
  ];
  if (current.scope === "server") {
    lines.push(
      `The global default is **${ai.label(global.provider, global.model)}**` +
        (global.scope === "default" ? " (built in)." : ".")
    );
  }

  const note = await healthNote(current.provider);
  if (note) lines.push(note);

  lines.push(
    "",
    "Change it with `/setchatbotai provider:<gemini|openai|ollama> model:<name> scope:<server|global>`.",
    "`scope` defaults to this server only. Pick `clear` to drop this server back to the global default."
  );

  await interaction.reply({ content: lines.join("\n"), flags: MessageFlags.Ephemeral });
}

async function clearOverride(interaction) {
  await ai.clearSettings(interaction.guild.id);
  const now = await ai.getSettings(interaction.guild.id);
  await interaction.reply({
    content:
      "Cleared this server's override. It now follows " +
      `${now.scope === "global" ? "the global default" : "the built-in default"}: ` +
      `**${ai.label(now.provider, now.model)}**.`,
    flags: MessageFlags.Ephemeral,
  });
}

async function setGemini(interaction, targetId, scope, model) {
  await ai.setSettings(targetId, "gemini", model);

  const lines = [
    `Chatbot AI set to **${ai.label("gemini", model || gemini.DEFAULT_MODEL)}** ${scopeText(scope)}.`,
  ];
  if (!model) lines.push(`No model given, so the default \`${gemini.DEFAULT_MODEL}\` is used.`);
  const note = await healthNote("gemini");
  if (note) lines.push(note);

  await interaction.reply({ content: lines.join("\n"), flags: MessageFlags.Ephemeral });
}

async function setOpenai(interaction, targetId, scope, model) {
  if (!model) {
    await interaction.reply({
      content:
        "OpenAI needs a model name, e.g. `/setchatbotai provider:openai model:gpt-4o-mini`. " +
        "The model option autocompletes with whatever the bot's API key can see.",
      flags: MessageFlags.Ephemeral,
    });
    return;
  }
  if (!openai.hasKey()) {
    await interaction.reply({
      content:
        "`OPENAI_API_KEY` isn't set on the bot, so OpenAI can't be used yet. " +
        "Add it to the bot's `.env` and restart, then run this again.",
      flags: MessageFlags.Ephemeral,
    });
    return;
  }

  await interaction.deferReply({ flags: MessageFlags.Ephemeral });

  // "unknown" means the endpoint won't list models, so the name can't be checked
  const known = await openai.hasModel(model);
  if (known === false) {
    await report(
      interaction,
      `The API key can't see a model called \`${model}\`. Check the name (the \`model\` ` +
        "option autocompletes with the ones it can use). The chatbot AI has been left as it was."
    );
    return;
  }

  await ai.setSettings(targetId, "openai", model);
  await report(
    interaction,
    `Chatbot AI set to **${ai.label("openai", model)}** ${scopeText(scope)}.` +
      (known === "unknown"
        ? "\nCouldn't check that model against the API, so it's set as given; watch the first reply."
        : "")
  );
}

async function setOllama(interaction, targetId, scope, model) {
  if (!model) {
    await interaction.reply({
      content:
        "Ollama needs a model name, e.g. `/setchatbotai provider:ollama model:llama3`. " +
        "Anything from <https://ollama.com/library> works; it gets installed automatically.",
      flags: MessageFlags.Ephemeral,
    });
    return;
  }

  // pulling a model takes minutes, so claim the interaction before anything else
  await interaction.deferReply({ flags: MessageFlags.Ephemeral });

  if (!(await ollama.reachable())) {
    await report(
      interaction,
      `Can't reach the Ollama server at \`${ollamaHost()}\`. ` +
        "Start it with `ollama serve` on the bot's host (install it from <https://ollama.com/download>), " +
        "or point `OLLAMA_HOST` at wherever it runs, then try again."
    );
    return;
  }

  let installed;
  try {
    installed = await ollama.hasModel(model);
  } catch (err) {
    await report(interaction, `Couldn't check the installed models: ${err?.message ?? err}`);
    return;
  }

  if (!installed) {
    await report(interaction, `Installing \`${model}\`, this can take a while...`);

    let lastEdit = 0;
    try {
      await ollama.pullModel(model, (evt) => {
        const now = Date.now();
        if (now - lastEdit < PROGRESS_EDIT_MS) return;
        lastEdit = now;
        // fire and forget: progress must never hold up the download
        report(interaction, progressLine(model, evt)).catch(() => {});
      });
    } catch (err) {
      await report(
        interaction,
        `Couldn't install \`${model}\`: ${err?.message ?? err}\n` +
          "Check the name against <https://ollama.com/library>. The chatbot AI has been left as it was."
      );
      return;
    }
  }

  await ai.setSettings(targetId, "ollama", model);
  await report(
    interaction,
    `Chatbot AI set to **${ai.label("ollama", model)}** ${scopeText(scope)}` +
      (installed ? " (already installed)." : " (model installed).")
  );
}

export default {
  data: new SlashCommandBuilder()
    .setName("setchatbotai")
    .setDescription("Bot owner only. Choose which AI answers in the chatbot channel.")
    .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
    .addStringOption((o) =>
      o
        .setName("provider")
        .setDescription("Which AI to use. Leave empty to see the current one.")
        .setRequired(false)
        .addChoices(
          { name: "gemini (Google, needs GEMINI_API_KEY)", value: "gemini" },
          { name: "openai (needs OPENAI_API_KEY)", value: "openai" },
          { name: "ollama (local, auto-installs the model)", value: "ollama" }
        )
    )
    .addStringOption((o) =>
      o
        .setName("model")
        .setDescription("Model name. Required for openai and ollama, optional for gemini.")
        .setRequired(false)
        .setAutocomplete(true)
    )
    .addStringOption((o) =>
      o
        .setName("scope")
        .setDescription("Where it applies. Defaults to this server only.")
        .setRequired(false)
        .addChoices(
          { name: "this server only", value: "server" },
          { name: "global: the default for every server", value: "global" },
          { name: "clear this server's setting and follow the global default", value: "clear" }
        )
    ),

  // suggest models the provider actually offers; typing your own is still fine
  async autocomplete(interaction) {
    if (!(await isBotOwner(interaction.client, interaction.user.id))) {
      await interaction.respond([]);
      return;
    }

    const raw = interaction.options.getFocused();
    const typed = raw.toLowerCase();
    const provider = interaction.options.getString("provider") ?? "gemini";

    let models = [];
    if (provider === "gemini") {
      models = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"];
    } else if (provider === "openai") {
      models = (await openai.listModels().catch(() => [])).filter((m) => !NON_CHAT.test(m));
    } else {
      models = await ollama.listModels().catch(() => []);
    }

    const matches = models.filter((m) => m.toLowerCase().includes(typed));
    const choices = matches.slice(0, 24).map((m) => ({ name: m, value: m }));

    // let them name something the list doesn't have (a new Ollama model to install)
    if (raw && raw.length <= 100 && !models.some((m) => m.toLowerCase() === typed)) {
      choices.unshift({
        name: provider === "ollama" ? `${raw} (install)` : raw,
        value: raw,
      });
    }
    await interaction.respond(choices.slice(0, 25));
  },

  async execute(interaction) {
    if (!(await isBotOwner(interaction.client, interaction.user.id))) {
      await interaction.reply({
        content: "Only the bot owner can change the chatbot AI.",
        flags: MessageFlags.Ephemeral,
      });
      return;
    }

    const provider = interaction.options.getString("provider");
    const model = interaction.options.getString("model")?.trim() || null;
    const scope = interaction.options.getString("scope") ?? "server";

    if (scope !== "global" && !interaction.guild) {
      await interaction.reply({
        content: "Run this in the server you want to change, or use `scope:global`.",
        flags: MessageFlags.Ephemeral,
      });
      return;
    }

    if (scope === "clear") {
      await clearOverride(interaction);
      return;
    }
    if (!provider) {
      await showCurrent(interaction);
      return;
    }

    const targetId = scope === "global" ? ai.GLOBAL_ID : interaction.guild.id;

    if (provider === "ollama") await setOllama(interaction, targetId, scope, model);
    else if (provider === "openai") await setOpenai(interaction, targetId, scope, model);
    else await setGemini(interaction, targetId, scope, model);
  },
};
