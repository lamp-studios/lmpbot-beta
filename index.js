import { readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { Client, Collection, GatewayIntentBits, Partials } from "discord.js";
import { config } from "./config.js";
import { initStorage } from "./utils/db.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.GuildMembers,
    GatewayIntentBits.MessageContent,
  ],
  partials: [Partials.Channel],
});

client.commands = new Collection();
client.startTime = Date.now();
client.ownerIds = new Set();

async function loadDir(subdir) {
  const dir = join(__dirname, subdir);
  const modules = [];
  for (const file of readdirSync(dir).filter((f) => f.endsWith(".js"))) {
    const imported = await import(pathToFileURL(join(dir, file)).href);
    modules.push({ name: file, mod: imported.default ?? imported });
  }
  return modules;
}

async function loadCommands() {
  for (const { name, mod } of await loadDir("commands")) {
    if (mod?.data && mod?.execute) {
      client.commands.set(mod.data.name, mod);
      console.log(`Loaded command: ${mod.data.name}`);
    } else {
      console.warn(`Skipped command ${name}: missing data/execute export`);
    }
  }
}

async function loadEvents() {
  for (const { name, mod } of await loadDir("events")) {
    if (!mod?.name || !mod?.execute) {
      console.warn(`Skipped event ${name}: missing name/execute export`);
      continue;
    }
    const handler = (...args) => mod.execute(...args, client);
    if (mod.once) client.once(mod.name, handler);
    else client.on(mod.name, handler);
    console.log(`Loaded event: ${mod.name}`);
  }
}

async function main() {
  await initStorage();

  await loadCommands();
  await loadEvents();

  await client.login(config.token);
}

main().catch((err) => {
  console.error("Fatal startup error:", err);
  process.exit(1);
});
