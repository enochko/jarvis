/**
 * Jarvis Agent Engine (Node.js edition) — HTTP service on 127.0.0.1:8000.
 * All LLM logic lives here; channels are thin clients (BR-001).
 *
 * Routes:
 *   GET  /health   -> { status, timestamp }
 *   POST /message  -> { text, success, duration_s }   body: { text, user_id?, session_id? }
 *
 * No npm dependencies: node:http + node:child_process only.
 */
import { spawn } from "node:child_process";
import { timingSafeEqual } from "node:crypto";
import { existsSync } from "node:fs";
import { createServer } from "node:http";
import { homedir } from "node:os";
import { delimiter, join } from "node:path";
import { pathToFileURL } from "node:url";

import { config } from "./lib/config.mjs";
import { readJsonBody, sendJson } from "./lib/http.mjs";
import { createLogger } from "./lib/logger.mjs";

const logger = createLogger("agent", config.logDir);

const ALLOWED_TOOLS = "Read,Write,Edit,Grep,Glob,LS"; // No Bash on the interactive path.

// ── Claude binary resolution ────────────────────────────────────────────────

/**
 * Find a directly executable claude binary. On Windows the npm shim is a .cmd
 * file, which Node can only run through a shell — so we resolve the real
 * claude.exe behind it and never pass user text through cmd.exe.
 */
export function resolveClaude() {
  if (config.claudePath) return config.claudePath;
  const isWin = process.platform === "win32";
  const names = isWin ? ["claude.exe"] : ["claude"];
  const dirs = (process.env.PATH || "").split(delimiter).filter(Boolean);
  if (isWin) dirs.push(join(homedir(), ".local", "bin"));

  for (const dir of dirs) {
    for (const name of names) {
      const p = join(dir, name);
      if (existsSync(p)) return p;
    }
    if (isWin && existsSync(join(dir, "claude.cmd"))) {
      const exe = join(dir, "node_modules", "@anthropic-ai", "claude-code", "bin", "claude.exe");
      if (existsSync(exe)) return exe;
    }
  }
  return null;
}

// ── Injection detection ─────────────────────────────────────────────────────

const INJECTION_PATTERNS = [
  /ignore\s+(previous|above|all)\s+instructions/i,
  /new\s+instructions\s*:/i,
  /\[SYSTEM\]/i,
  /<\|im_start\|>/i,
  /you\s+are\s+now\s+/i,
  /disregard\s+(all|previous|your)/i,
];

/**
 * Returns the matching pattern or null. Logs up to 200 chars on a match —
 * deliberate exception to the "length only" rule for forensic review.
 */
function checkInjection(text) {
  for (const pattern of INJECTION_PATTERNS) {
    if (pattern.test(text)) {
      logger.warn(`Prompt injection blocked | pattern=${pattern} | text=${JSON.stringify(text.slice(0, 200))}`);
      return pattern;
    }
  }
  return null;
}

// ── Auth ────────────────────────────────────────────────────────────────────

function secretOk(provided, expected) {
  if (!expected) return true;
  const a = Buffer.from(String(provided || ""));
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

// ── Serialised execution (one claude process at a time) ─────────────────────

let queue = Promise.resolve();
function serialised(fn) {
  const run = queue.then(fn, fn);
  queue = run.catch(() => {});
  return run;
}

const activeProcs = new Set();

function writeRestrictionPrefix() {
  const dirs = config.writeDirs.map((d) => `  - ${d}`).join("\n");
  return (
    `IMPORTANT: You may only write or edit files in these directories:\n${dirs}\n` +
    `Do NOT write to any other location.\n\n`
  );
}

const QUOTA_KEYWORDS = [
  "rate limit", "rate_limit", "429", "quota", "usage limit",
  "too many requests", "capacity", "overloaded", "throttl",
];

/**
 * Run `claude -p` non-interactively. The prompt goes in via stdin, so it is
 * never parsed by a shell and has no command-line length limit.
 */
export function runClaude(prompt, claudePath, model = config.defaultModel) {
  const fullPrompt = writeRestrictionPrefix() + prompt;
  const args = ["-p", "--model", model, "--output-format", "text", "--allowedTools", ALLOWED_TOOLS];

  return serialised(
    () =>
      new Promise((resolvePromise) => {
        const start = Date.now();
        const elapsed = () => Math.round((Date.now() - start) / 100) / 10;
        logger.debug(`claude start | model=${model} | prompt_len=${fullPrompt.length}`);

        if (!claudePath) {
          logger.error("claude CLI not found. Install Claude Code or set CLAUDE_PATH.");
          resolvePromise({ success: false, text: "claude CLI not found. Check CLAUDE_PATH.", duration_s: 0 });
          return;
        }

        let child;
        try {
          child = spawn(claudePath, args, { cwd: homedir(), windowsHide: true, stdio: ["pipe", "pipe", "pipe"] });
        } catch (err) {
          logger.error(`claude spawn failed: ${err.message}`);
          resolvePromise({ success: false, text: "Could not start claude CLI. Check logs.", duration_s: 0 });
          return;
        }
        activeProcs.add(child);

        const out = [];
        const errOut = [];
        let timedOut = false;
        child.stdout.on("data", (c) => out.push(c));
        child.stderr.on("data", (c) => errOut.push(c));
        child.stdin.on("error", () => {}); // child may exit before reading stdin
        child.stdin.end(fullPrompt, "utf8");

        const timer = setTimeout(() => {
          timedOut = true;
          logger.error(`claude timed out after ${config.taskTimeoutS}s`);
          child.kill();
        }, config.taskTimeoutS * 1000);

        child.on("error", (err) => {
          clearTimeout(timer);
          activeProcs.delete(child);
          logger.error(`claude process error: ${err.message}`);
          resolvePromise({ success: false, text: "claude CLI could not be run. Check logs.", duration_s: elapsed() });
        });

        child.on("close", (code) => {
          clearTimeout(timer);
          activeProcs.delete(child);
          const output = Buffer.concat(out).toString("utf8").trim();
          const err = Buffer.concat(errOut).toString("utf8").trim();
          if (err) logger.debug(`stderr: ${err.slice(0, 500)}`);

          if (timedOut) {
            resolvePromise({ success: false, text: "Request timed out.", duration_s: config.taskTimeoutS });
            return;
          }

          // stderr is authoritative; only inspect stdout when stderr is empty, so a
          // reply that merely *discusses* rate limits isn't misread as one.
          const haystack = (err || (code !== 0 ? output : "")).toLowerCase();
          if (QUOTA_KEYWORDS.some((kw) => haystack.includes(kw))) {
            logger.warn("Quota/rate-limit detected");
            resolvePromise({ success: false, text: "Claude quota limit reached. Try again in an hour.", duration_s: elapsed() });
            return;
          }

          if (code !== 0 && /authenticat|log ?in|oauth|api key/i.test(err || output)) {
            logger.error(`claude not authenticated: ${(err || output).slice(0, 300)}`);
            resolvePromise({
              success: false,
              text: "Claude CLI is not logged in. Open a terminal, run `claude`, and log in with /login — then try again.",
              duration_s: elapsed(),
            });
            return;
          }

          if (code !== 0) {
            // claude -p sometimes reports errors on stdout with an empty stderr.
            logger.error(`claude exit ${code}: ${(err || output).slice(0, 300)}`);
            resolvePromise({ success: false, text: `Agent error (exit ${code}). Check logs.`, duration_s: elapsed() });
            return;
          }

          logger.info(`claude OK | ${elapsed()}s | output=${output.length} chars`);
          resolvePromise({ success: true, text: output, duration_s: elapsed() });
        });
      }),
  );
}

// ── Server ──────────────────────────────────────────────────────────────────

/**
 * Start the agent engine. Resolves once listening.
 * @returns {Promise<{ close: () => Promise<void> }>}
 */
export async function startAgent() {
  const claudePath = resolveClaude();
  if (!config.agentSecret) {
    logger.warn("JARVIS_AGENT_SECRET is not set — /message has no auth. Set it before exposing the agent beyond localhost.");
  }
  if (claudePath) logger.info(`claude binary: ${claudePath}`);
  else logger.warn("claude binary not found — all requests will fail. Install Claude Code or set CLAUDE_PATH.");

  const server = createServer(async (req, res) => {
    try {
      const url = new URL(req.url, "http://localhost");

      if (req.method === "GET" && url.pathname === "/health") {
        sendJson(res, 200, { status: "ok", timestamp: new Date().toISOString() });
        return;
      }

      if (req.method === "POST" && url.pathname === "/message") {
        if (!secretOk(req.headers["x-jarvis-secret"], config.agentSecret)) {
          logger.warn("Rejected request with invalid agent secret");
          sendJson(res, 403, { detail: "Forbidden" });
          return;
        }
        const body = await readJsonBody(req);
        if (typeof body.text !== "string" || !body.text.trim()) {
          sendJson(res, 422, { detail: "Field 'text' (non-empty string) is required." });
          return;
        }
        // Log length only — never content (may contain Finance/Health data).
        logger.info(`Message from user=${body.user_id ?? "-"} | len=${body.text.length} chars`);
        if (checkInjection(body.text)) {
          sendJson(res, 400, { detail: "Message blocked: matched prompt injection pattern." });
          return;
        }
        const result = await runClaude(body.text, claudePath);
        sendJson(res, 200, result);
        return;
      }

      sendJson(res, 404, { detail: "Not found" });
    } catch (err) {
      if (err.status) {
        sendJson(res, err.status, { detail: err.message });
      } else {
        logger.error(`Unhandled error: ${err.stack || err}`);
        sendJson(res, 500, { detail: "Internal error" });
      }
    }
  });

  // claude calls can take up to taskTimeoutS; don't let Node cut the socket first.
  server.requestTimeout = (config.taskTimeoutS + 30) * 1000;

  await new Promise((resolveListen, reject) => {
    server.once("error", reject);
    server.listen(config.agentPort, config.agentHost, resolveListen);
  });
  logger.info(`Jarvis agent engine listening on http://${config.agentHost}:${config.agentPort}`);

  return {
    async close() {
      for (const child of activeProcs) {
        child.kill();
        logger.info(`claude subprocess PID ${child.pid} terminated`);
      }
      const closed = new Promise((r) => server.close(() => r()));
      server.closeAllConnections();
      await closed;
    },
  };
}

// Direct execution: node node/agent.mjs
if (import.meta.url === pathToFileURL(process.argv[1] || "").href) {
  const agent = await startAgent();
  const stop = async () => {
    await agent.close();
    process.exit(0);
  };
  process.on("SIGINT", stop);
  process.on("SIGTERM", stop);
}
