import { config } from "../config.js";

const INTERVAL_MS = 60_000;

// Strip any pre-existing query string so we don't double up params and confuse
// Kuma (duplicate keys get parsed as arrays/objects -> wrong status).
function normalizeKumaUrl(raw) {
  if (!raw) return null;
  try {
    const u = new URL(raw);
    return `${u.origin}${u.pathname}`;
  } catch {
    return raw.split("?")[0];
  }
}

const PUSH_URL = normalizeKumaUrl(config.kumaPushUrl);
const PUSHGATEWAY_URL = config.pushgatewayUrl || null;

console.log(
  `[heartbeat] module loaded, PUSH_URL set: ${Boolean(PUSH_URL)}, PUSHGATEWAY set: ${Boolean(PUSHGATEWAY_URL)}`
);

/**
 * Start the monitoring heartbeat loop. No-op if neither endpoint is configured.
 * @param {import("discord.js").Client} client
 */
export function startHeartbeat(client) {
  if (!PUSH_URL && !PUSHGATEWAY_URL) {
    console.log("[heartbeat] no KUMA_PUSH_URL or PUSHGATEWAY_URL set; heartbeat disabled");
    return;
  }

  async function push() {
    const latency = client.ws.ping;
    const pingMs = Number.isFinite(latency) && latency >= 0 ? Math.round(latency) : 0;

    // Uptime Kuma push
    if (PUSH_URL) {
      const msg = client.isReady() ? "ready" : "connecting";
      const params = new URLSearchParams({ status: "up", msg, ping: String(pingMs) });
      try {
        const res = await fetch(`${PUSH_URL}?${params}`, {
          signal: AbortSignal.timeout(10_000),
        });
        console.log(`[heartbeat] push -> HTTP ${res.status} (msg=${msg}, ping=${pingMs})`);
      } catch (err) {
        console.log(`[heartbeat] push failed: ${err}`);
      }
    }

    // Prometheus Pushgateway push (independent of Kuma)
    if (PUSHGATEWAY_URL) {
      const up = client.isReady() ? 1 : 0;
      const body =
        "# TYPE lmpbot_up gauge\n" +
        `lmpbot_up ${up}\n` +
        "# TYPE lmpbot_ping_ms gauge\n" +
        `lmpbot_ping_ms ${pingMs}\n`;
      try {
        const url = `${PUSHGATEWAY_URL.replace(/\/$/, "")}/metrics/job/lmpbot`;
        const res = await fetch(url, {
          method: "POST",
          body,
          signal: AbortSignal.timeout(10_000),
        });
        console.log(`[heartbeat] pushgateway -> HTTP ${res.status}`);
      } catch (err) {
        console.log(`[heartbeat] pushgateway push failed: ${err}`);
      }
    }
  }

  push().catch(() => {});
  setInterval(() => push().catch(() => {}), INTERVAL_MS);
}
