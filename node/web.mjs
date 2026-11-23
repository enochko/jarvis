/**
 * Jarvis web channel — local chat page on http://127.0.0.1:3000.
 * Thin client: forwards messages to the agent engine and adds the shared
 * secret server-side, so the secret never reaches the browser.
 *
 * Guards against other websites driving the agent through the browser:
 *   - Host header must be this server (blocks DNS rebinding)
 *   - Origin, when sent, must be this server (blocks cross-site POSTs)
 *   - Content-Type must be application/json (forces a CORS preflight we never answer)
 */
import { readFileSync } from "node:fs";
import { createServer } from "node:http";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { agentHealth, callAgent } from "./lib/client.mjs";
import { config } from "./lib/config.mjs";
import { readJsonBody, sendJson } from "./lib/http.mjs";
import { createLogger } from "./lib/logger.mjs";

const PAGE = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "public", "index.html"));

export async function startWeb() {
  const logger = createLogger("web", config.logDir);
  const port = config.webPort;
  const allowedHosts = new Set([`127.0.0.1:${port}`, `localhost:${port}`]);
  const allowedOrigins = new Set([...allowedHosts].map((h) => `http://${h}`));

  const server = createServer(async (req, res) => {
    try {
      if (!allowedHosts.has(req.headers.host || "")) {
        sendJson(res, 421, { detail: "Misdirected request" });
        return;
      }
      const url = new URL(req.url, `http://${req.headers.host}`);

      if (req.method === "GET" && url.pathname === "/") {
        res.writeHead(200, {
          "content-type": "text/html; charset=utf-8",
          "content-security-policy": "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; frame-ancestors 'none'",
          "x-frame-options": "DENY",
        });
        res.end(PAGE);
        return;
      }

      if (req.method === "GET" && url.pathname === "/api/health") {
        try {
          sendJson(res, 200, await agentHealth());
        } catch {
          sendJson(res, 503, { status: "unreachable" });
        }
        return;
      }

      if (req.method === "POST" && url.pathname === "/api/message") {
        const origin = req.headers.origin;
        if (origin && !allowedOrigins.has(origin)) {
          logger.warn(`Rejected cross-origin request from ${origin}`);
          sendJson(res, 403, { detail: "Forbidden" });
          return;
        }
        if (!(req.headers["content-type"] || "").startsWith("application/json")) {
          sendJson(res, 415, { detail: "Content-Type must be application/json" });
          return;
        }
        const body = await readJsonBody(req);
        if (typeof body.text !== "string" || !body.text.trim()) {
          sendJson(res, 422, { detail: "Field 'text' is required." });
          return;
        }
        logger.info(`Web message | len=${body.text.length} chars`);
        sendJson(res, 200, { text: await callAgent(body.text, "web", logger) });
        return;
      }

      sendJson(res, 404, { detail: "Not found" });
    } catch (err) {
      if (err.status) sendJson(res, err.status, { detail: err.message });
      else {
        logger.error(`Unhandled error: ${err.stack || err}`);
        sendJson(res, 500, { detail: "Internal error" });
      }
    }
  });
  server.requestTimeout = (config.taskTimeoutS + 60) * 1000;

  await new Promise((resolveListen, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", resolveListen);
  });
  const url = `http://127.0.0.1:${port}`;
  logger.info(`Jarvis web chat on ${url}`);

  return {
    url,
    async close() {
      const closed = new Promise((r) => server.close(() => r()));
      server.closeAllConnections();
      await closed;
    },
  };
}

// Direct execution: node node/web.mjs (agent must already be running)
if (import.meta.url === pathToFileURL(process.argv[1] || "").href) {
  const web = await startWeb();
  const stop = async () => {
    await web.close();
    process.exit(0);
  };
  process.on("SIGINT", stop);
  process.on("SIGTERM", stop);
}
