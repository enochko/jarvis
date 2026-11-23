/**
 * Jarvis launcher — starts the agent engine plus every channel that can run:
 *   - web chat on http://127.0.0.1:3000 (always; opens the browser)
 *   - Telegram bot (only if TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USERS are set)
 *   - terminal chat (with --cli, instead of opening the browser)
 *
 * Usage: node node/start.mjs [--cli] [--no-browser]
 */
import { spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import { createInterface } from "node:readline/promises";

import { config } from "./lib/config.mjs";

const args = new Set(process.argv.slice(2));
const cliMode = args.has("--cli");
const openBrowser = !cliMode && !args.has("--no-browser");

// Without a configured secret, generate one for this run. All channels run in
// this process and read it from `config`, so the agent is never left open.
if (!config.agentSecret) {
  config.agentSecret = randomBytes(24).toString("hex");
}

const { startAgent } = await import("./agent.mjs");
const { startWeb } = await import("./web.mjs");
const { startBot } = await import("./bot.mjs");
const { callAgent } = await import("./lib/client.mjs");

const handles = [];

try {
  handles.push(await startAgent());
} catch (err) {
  console.error(
    err.code === "EADDRINUSE"
      ? `Port ${config.agentPort} is busy — is Jarvis already running?`
      : `Agent failed to start: ${err.message}`,
  );
  process.exit(1);
}

let web;
try {
  web = await startWeb();
  handles.push(web);
} catch (err) {
  console.error(
    err.code === "EADDRINUSE"
      ? `Port ${config.webPort} is busy — set JARVIS_WEB_PORT to another port.`
      : `Web chat failed to start: ${err.message}`,
  );
}

if (config.telegramToken) {
  try {
    handles.push(startBot());
  } catch (err) {
    console.error(`Telegram bot not started: ${err.message}`);
  }
}

async function shutdown() {
  console.log("\nJarvis shutting down...");
  await Promise.allSettled(handles.map((h) => (h.stop ? h.stop() : h.close())));
  process.exit(0);
}
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

if (web) console.log(`\n  Jarvis is running — open ${web.url}\n  Press Ctrl+C to stop.\n`);

if (openBrowser && web && process.platform === "win32") {
  // Fixed URL, no user input — safe to hand to `start`.
  spawn("cmd.exe", ["/c", "start", "", web.url], { detached: true, stdio: "ignore", windowsHide: true }).unref();
} else if (openBrowser && web) {
  const opener = process.platform === "darwin" ? "open" : "xdg-open";
  spawn(opener, [web.url], { detached: true, stdio: "ignore" }).on("error", () => {}).unref();
}

if (cliMode) {
  const quietLogger = { error: () => {} };
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  rl.on("close", shutdown);
  console.log('Terminal chat — type a message, "exit" to quit.\n');
  for (;;) {
    let line;
    try {
      line = (await rl.question("you › ")).trim();
    } catch {
      break; // readline closed (Ctrl+C / Ctrl+D)
    }
    if (!line) continue;
    if (line === "exit" || line === "quit") break;
    process.stdout.write("jarvis is thinking...\r");
    const reply = await callAgent(line, "cli", quietLogger);
    console.log(`jarvis › ${reply}\n`);
  }
  await shutdown();
}
