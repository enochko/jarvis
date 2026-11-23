/**
 * Jarvis Telegram bot (Node.js edition) — thin client, long polling via the
 * Telegram Bot API with built-in fetch. No npm dependencies.
 *
 * Env: TELEGRAM_BOT_TOKEN (required), TELEGRAM_ALLOWED_USERS (required,
 * comma-separated user IDs), JARVIS_AGENT_SECRET, JARVIS_AGENT_URL.
 */
import { pathToFileURL } from "node:url";

import { agentHealth, callAgent } from "./lib/client.mjs";
import { config } from "./lib/config.mjs";
import { createLogger } from "./lib/logger.mjs";

const POLL_TIMEOUT_S = 50;
const MAX_BACKOFF_MS = 60_000;

/** Split text into Telegram-sized chunks (limit 4096), preferring line breaks. */
export function chunkText(text, maxLen = 4000) {
  if (!text) return ["(empty response)"];
  const chunks = [];
  let current = "";
  for (const line of text.split("\n")) {
    // Hard-split single lines that alone exceed the limit.
    for (let i = 0; i < Math.max(line.length, 1); i += maxLen) {
      const piece = line.slice(i, i + maxLen);
      if (current && current.length + piece.length + 1 > maxLen) {
        chunks.push(current);
        current = "";
      }
      current = current ? `${current}\n${piece}` : piece;
    }
  }
  if (current) chunks.push(current);
  return chunks;
}

/**
 * Start the bot. Returns a handle with stop(). Throws if config is incomplete.
 */
export function startBot() {
  const logger = createLogger("bot", config.logDir);
  if (!config.telegramToken) throw new Error("TELEGRAM_BOT_TOKEN is not set");
  if (config.telegramAllowedUsers.size === 0) {
    // The agent can read and write files, so an open bot is not acceptable.
    throw new Error("TELEGRAM_ALLOWED_USERS is empty — refusing to start an open bot");
  }

  const api = `https://api.telegram.org/bot${config.telegramToken}`;
  const controller = new AbortController();
  let stopped = false;

  async function tg(method, params, timeoutMs = 15_000) {
    const resp = await fetch(`${api}/${method}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(params),
      signal: AbortSignal.any([controller.signal, AbortSignal.timeout(timeoutMs)]),
    });
    const data = await resp.json().catch(() => ({}));
    if (!data.ok) {
      const err = new Error(`Telegram ${method} failed: ${resp.status} ${data.description || ""}`.trim());
      err.status = resp.status;
      throw err;
    }
    return data.result;
  }

  async function reply(chatId, text) {
    for (const chunk of chunkText(text)) {
      try {
        await tg("sendMessage", { chat_id: chatId, text: chunk });
      } catch (err) {
        logger.error(err.message);
      }
    }
  }

  async function handleUpdate(update) {
    const msg = update.message;
    if (!msg || typeof msg.text !== "string") return;
    const userId = msg.from?.id;
    const chatId = msg.chat.id;

    if (!config.telegramAllowedUsers.has(userId)) {
      logger.warn(`Blocked unauthorised user ${userId}`);
      await reply(chatId, "Not authorised.");
      return;
    }

    const text = msg.text;
    if (text === "/start" || text.startsWith("/start@")) {
      await reply(chatId, "Jarvis online. Send me a message.");
      return;
    }
    if (text === "/health" || text.startsWith("/health@")) {
      try {
        const h = await agentHealth();
        await reply(chatId, `Agent engine: ${h.status} (${h.timestamp})`);
      } catch (err) {
        await reply(chatId, `Agent engine unreachable: ${err.message}`);
      }
      return;
    }
    if (text.startsWith("/")) return; // ignore unknown commands

    // Log length only — never content.
    logger.info(`Message from ${userId} | len=${text.length} chars`);

    // Telegram expires the typing indicator after ~5 s; refresh every 4 s.
    const sendTyping = () => tg("sendChatAction", { chat_id: chatId, action: "typing" }).catch(() => {});
    sendTyping();
    const typing = setInterval(sendTyping, 4000);
    let response;
    try {
      response = await callAgent(text, userId, logger);
    } finally {
      clearInterval(typing);
    }
    await reply(chatId, response);
  }

  async function pollLoop() {
    let offset = 0;
    let backoff = 1000;
    logger.info("Jarvis Telegram bot polling for messages...");
    while (!stopped) {
      try {
        const updates = await tg(
          "getUpdates",
          { offset, timeout: POLL_TIMEOUT_S, allowed_updates: ["message"] },
          (POLL_TIMEOUT_S + 10) * 1000,
        );
        backoff = 1000;
        for (const u of updates) {
          offset = u.update_id + 1;
          // Handle messages concurrently; the agent serialises claude calls itself.
          handleUpdate(u).catch((err) => logger.error(`Handler error: ${err.stack || err}`));
        }
      } catch (err) {
        if (stopped) break;
        if (err.status === 401 || err.status === 404) {
          logger.error("Telegram rejected the bot token — bot stopped. Check TELEGRAM_BOT_TOKEN.");
          return;
        }
        if (err.status === 409) {
          logger.error("Another instance is polling this bot (HTTP 409). Retrying...");
        } else {
          logger.warn(`Polling error: ${err.message} — retry in ${backoff / 1000}s`);
        }
        await new Promise((r) => setTimeout(r, backoff));
        backoff = Math.min(backoff * 2, MAX_BACKOFF_MS);
      }
    }
  }

  const done = pollLoop();
  return {
    async stop() {
      stopped = true;
      controller.abort();
      await done.catch(() => {});
    },
  };
}

// Direct execution: node node/bot.mjs
if (import.meta.url === pathToFileURL(process.argv[1] || "").href) {
  const bot = startBot();
  const stop = async () => {
    await bot.stop();
    process.exit(0);
  };
  process.on("SIGINT", stop);
  process.on("SIGTERM", stop);
}
