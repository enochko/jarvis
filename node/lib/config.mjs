/**
 * Shared configuration for all Jarvis services (Node.js edition).
 *
 * Loads `.env` from the repo root if present (Node's built-in loader, no
 * dependencies), then reads the same environment variables as the Python
 * version so both implementations stay interchangeable.
 */
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");

const envFile = join(REPO_ROOT, ".env");
if (existsSync(envFile)) {
  process.loadEnvFile(envFile);
}

/** Expand a leading `~` to the user's home directory. */
export function expandHome(p) {
  if (p === "~") return homedir();
  if (p.startsWith("~/") || p.startsWith("~\\")) return join(homedir(), p.slice(2));
  return p;
}

function env(name, fallback = "") {
  const v = process.env[name];
  return v === undefined || v.trim() === "" ? fallback : v.trim();
}

function list(value) {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export const config = {
  logDir: expandHome(env("JARVIS_LOG_DIR", "~/Obsidian/aaa-claude/jarvis-logs")),

  // Agent engine
  agentHost: "127.0.0.1",
  agentPort: Number(env("JARVIS_AGENT_PORT", "8000")),
  agentUrl: env("JARVIS_AGENT_URL", ""), // derived below if empty
  agentSecret: env("JARVIS_AGENT_SECRET", ""),
  claudePath: env("CLAUDE_PATH", ""),
  defaultModel: env("JARVIS_DEFAULT_MODEL", "sonnet"),
  taskTimeoutS: Number(env("JARVIS_TASK_TIMEOUT", "120")),
  writeDirs: list(
    env(
      "JARVIS_WRITE_DIRS",
      "~/Obsidian/aaa-claude/claude-outbox,~/Obsidian/aaa-claude/jarvis-memory",
    ),
  ).map(expandHome),

  // Web channel
  webPort: Number(env("JARVIS_WEB_PORT", "3000")),

  // Telegram channel
  telegramToken: env("TELEGRAM_BOT_TOKEN", ""),
  // TELEGRAM_ALLOWED_USERS is canonical; ALLOWED_USERS kept for older .env files.
  telegramAllowedUsers: new Set(
    list(env("TELEGRAM_ALLOWED_USERS", env("ALLOWED_USERS", ""))).map(Number),
  ),
};

if (!config.agentUrl) {
  config.agentUrl = `http://${config.agentHost}:${config.agentPort}`;
}
