#!/usr/bin/env python3
"""
Jarvis Telegram Bot
Thin client — all logic lives in the agent engine.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# ── Config ────────────────────────────────────────────────────────────────────

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_USERS = set(
    int(uid.strip())
    for uid in os.environ.get("TELEGRAM_ALLOWED_USERS", "").split(",")
    if uid.strip()
)
AGENT_URL = "http://127.0.0.1:8000"
LOG_DIR = Path("~/Obsidian/aaa-claude/jarvis-logs").expanduser()

# ── Logging ───────────────────────────────────────────────────────────────────

LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"bot_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("bot")


# ── Auth guard ────────────────────────────────────────────────────────────────

def is_authorised(update: Update) -> bool:
    uid = update.effective_user.id
    if ALLOWED_USERS and uid not in ALLOWED_USERS:
        logger.warning(f"Blocked unauthorised user {uid}")
        return False
    return True


# ── Agent call ────────────────────────────────────────────────────────────────

async def call_agent(text: str, user_id: int) -> str:
    async with httpx.AsyncClient(timeout=150.0) as client:
        try:
            resp = await client.post(
                f"{AGENT_URL}/message",
                json={"text": text, "user_id": str(user_id)},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["text"]
        except httpx.ConnectError:
            logger.error("Agent engine not reachable on localhost:8000")
            return "Agent engine is not running. Check the jarvis-agent launchd service."
        except Exception as e:
            logger.error(f"Agent call failed: {e}")
            return f"Error contacting agent engine: {e}"


# ── Chunk helper (Telegram 4096 char limit) ───────────────────────────────────

def chunk_text(text: str, max_len: int = 4000) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks, current = [], []
    current_len = 0
    for line in text.split("\n"):
        if current_len + len(line) + 1 > max_len:
            chunks.append("\n".join(current))
            current, current_len = [], 0
        current.append(line)
        current_len += len(line) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks


# ── Handlers ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorised(update):
        return
    await update.message.reply_text("Jarvis online. Send me a message.")


async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorised(update):
        return
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(f"{AGENT_URL}/health")
            data = resp.json()
            await update.message.reply_text(f"Agent engine: {data['status']} ({data['timestamp']})")
        except Exception as e:
            await update.message.reply_text(f"Agent engine unreachable: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorised(update):
        await update.message.reply_text("Not authorised.")
        return

    user_id = update.effective_user.id
    text = update.message.text

    # Typing indicator while agent runs
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    logger.info(f"Message from {user_id}: {text[:100]}")
    response = await call_agent(text, user_id)

    for chunk in chunk_text(response):
        await update.message.reply_text(chunk)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    logger.info("Jarvis Telegram bot starting")
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("health", cmd_health))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Polling for messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()