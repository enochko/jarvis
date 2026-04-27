#!/usr/bin/env python3
"""
jarvis.bot — Jarvis Telegram Bot
==================================
Thin client — all LLM logic lives in the agent engine (jarvis.agent).

Environment variables:
    TELEGRAM_BOT_TOKEN      Required. Telegram bot token from @BotFather.
    TELEGRAM_ALLOWED_USERS  Comma-separated Telegram user IDs to whitelist.
                            Empty = allow all (not recommended for production).
    JARVIS_AGENT_SECRET     Shared secret matching agent's JARVIS_AGENT_SECRET.
    JARVIS_AGENT_URL        Agent engine base URL (default: http://127.0.0.1:8000).
"""

import asyncio
import contextlib
import os
from pathlib import Path

import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from jarvis.logging_config import configure_logging

# ── Config ────────────────────────────────────────────────────────────────────

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN env var not set")

ALLOWED_USERS: set[int] = set(
    int(uid.strip())
    for uid in os.environ.get("TELEGRAM_ALLOWED_USERS", "").split(",")
    if uid.strip()
)

AGENT_URL = os.environ.get("JARVIS_AGENT_URL", "http://127.0.0.1:8000")

AGENT_SECRET = os.environ.get("JARVIS_AGENT_SECRET", "")

LOG_DIR = Path("~/Obsidian/aaa-claude/jarvis-logs").expanduser()

# ── Logging ───────────────────────────────────────────────────────────────────

logger = configure_logging("bot", LOG_DIR)

# ── Auth guard ────────────────────────────────────────────────────────────────

def is_authorised(update: Update) -> bool:
    uid = update.effective_user.id
    if ALLOWED_USERS and uid not in ALLOWED_USERS:
        logger.warning(f"Blocked unauthorised user {uid}")
        return False
    return True


# ── Agent call ────────────────────────────────────────────────────────────────

async def call_agent(text: str, user_id: int) -> str:
    headers = {"x-jarvis-secret": AGENT_SECRET} if AGENT_SECRET else {}
    async with httpx.AsyncClient(timeout=150.0) as client:
        try:
            resp = await client.post(
                f"{AGENT_URL}/message",
                json={"text": text, "user_id": str(user_id)},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["text"]
        except httpx.ConnectError:
            logger.error("Agent engine not reachable — is jarvis-agent launchd service running?")
            return "Agent engine is not running. Check the jarvis-agent launchd service."
        except httpx.TimeoutException:
            logger.error("Agent engine timed out")
            return "Agent took too long to respond. It may still be running — try again in a moment."
        except httpx.HTTPStatusError as e:
            logger.error(f"Agent HTTP {e.response.status_code}")
            if e.response.status_code == 400:
                return "Message blocked by agent (matched injection pattern)."
            return f"Agent returned an error ({e.response.status_code}). Check logs."
        except Exception:
            logger.exception("Unexpected error calling agent")
            return "Unexpected error contacting agent. Check logs."


# ── Typing indicator ──────────────────────────────────────────────────────────

async def _typing_loop(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Re-send typing indicator every 4s until cancelled. Telegram expires it after ~5s."""
    while True:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        await asyncio.sleep(4)


# ── Chunk helper (Telegram 4096 char limit) ───────────────────────────────────

def chunk_text(text: str, max_len: int = 4000) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    current: list[str] = []
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

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorised(update):
        return
    await update.message.reply_text("Jarvis online. Send me a message.")


async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorised(update):
        return
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(f"{AGENT_URL}/health")
            data = resp.json()
            await update.message.reply_text(
                f"Agent engine: {data['status']} ({data['timestamp']})"
            )
        except Exception as e:
            await update.message.reply_text(f"Agent engine unreachable: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorised(update):
        await update.message.reply_text("Not authorised.")
        return

    user_id = update.effective_user.id
    text = update.message.text

    # Log message length only — never log content (may contain Finance/Health data)
    logger.info(f"Message from {user_id} | len={len(text)} chars")

    # Typing indicator loops until agent responds (single send_chat_action expires in ~5s)
    typing_task = asyncio.create_task(_typing_loop(context, update.effective_chat.id))
    try:
        response = await call_agent(text, user_id)
    finally:
        typing_task.cancel()
        # suppress CancelledError from the typing task itself — expected cancellation path.
        # A CancelledError from the outer coroutine propagates normally past this block.
        with contextlib.suppress(asyncio.CancelledError):
            await typing_task

    for chunk in chunk_text(response):
        await update.message.reply_text(chunk)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    logger.info("Jarvis Telegram bot starting")
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("health", cmd_health))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Polling for messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
