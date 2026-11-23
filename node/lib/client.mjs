/**
 * Thin HTTP client used by every channel to talk to the agent engine.
 * Channels never call an LLM themselves (BR-001).
 */
import { config } from "./config.mjs";

/**
 * Send a message to the agent. Always resolves to a user-facing string.
 * @param {string} text
 * @param {string} userId
 * @param {{ error: (m: string) => void }} logger
 */
export async function callAgent(text, userId, logger) {
  const headers = { "content-type": "application/json" };
  if (config.agentSecret) headers["x-jarvis-secret"] = config.agentSecret;

  let resp;
  try {
    resp = await fetch(`${config.agentUrl}/message`, {
      method: "POST",
      headers,
      body: JSON.stringify({ text, user_id: String(userId) }),
      signal: AbortSignal.timeout((config.taskTimeoutS + 30) * 1000),
    });
  } catch (err) {
    if (err.name === "TimeoutError") {
      logger.error("Agent engine timed out");
      return "Agent took too long to respond. It may still be running — try again in a moment.";
    }
    logger.error(`Agent engine not reachable: ${err.cause?.code || err.message}`);
    return "Agent engine is not running. Start Jarvis with start-jarvis.cmd.";
  }

  if (!resp.ok) {
    logger.error(`Agent HTTP ${resp.status}`);
    if (resp.status === 400) return "Message blocked by agent (matched injection pattern).";
    if (resp.status === 403) return "Agent rejected the shared secret. Check JARVIS_AGENT_SECRET.";
    return `Agent returned an error (${resp.status}). Check logs.`;
  }
  try {
    const data = await resp.json();
    return data.text;
  } catch {
    logger.error("Agent returned invalid JSON");
    return "Unexpected response from agent. Check logs.";
  }
}

/** @returns {Promise<{ status: string, timestamp: string }>} */
export async function agentHealth() {
  const resp = await fetch(`${config.agentUrl}/health`, { signal: AbortSignal.timeout(5000) });
  return resp.json();
}
