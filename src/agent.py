#!/usr/bin/env python3
"""
Jarvis Agent Engine
FastAPI service on localhost:8000.
All LLM logic lives here — channels are thin clients.
"""

import asyncio
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

# ── Config ────────────────────────────────────────────────────────────────────

LOG_DIR = Path("~/Obsidian/aaa-claude/jarvis-logs").expanduser()
CLAUDE_PATH = "/Users/enochko/.local/bin/claude"   # update if `which claude` differs
DEFAULT_MODEL = "sonnet"
TASK_TIMEOUT = 120   # seconds; generous for interactive use

WRITE_DIRS = [
    "~/Obsidian/aaa-claude/claude-outbox",
    "~/Obsidian/aaa-claude/jarvis-memory",
]

# ── Logging ───────────────────────────────────────────────────────────────────

LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"agent_{datetime.now().strftime('%Y%m%d')}.log"

file_handler = RotatingFileHandler(
    log_file,
    maxBytes=5 * 1024 * 1024,   # 5MB per file
    backupCount=3,               # keep .log, .log.1, .log.2, .log.3
    encoding="utf-8",
)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))

logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, stream_handler])

# Suppress noisy internals
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

logger = logging.getLogger("agent")

# ── FastAPI ───────────────────────────────────────────────────────────────────

app = FastAPI(title="Jarvis Agent Engine", version="0.1.0")


class MessageRequest(BaseModel):
    text: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class MessageResponse(BaseModel):
    text: str
    success: bool
    duration_s: float


# ── Write restriction prompt prefix ──────────────────────────────────────────

def _write_restriction_prefix() -> str:
    expanded = [str(Path(d).expanduser()) for d in WRITE_DIRS]
    dirs = "\n".join(f"  - {d}" for d in expanded)
    return (
        f"IMPORTANT: You may only write or edit files in these directories:\n"
        f"{dirs}\n"
        f"Do NOT write to any other location.\n\n"
    )


# ── Core execution ────────────────────────────────────────────────────────────

async def run_claude(prompt: str, model: str = DEFAULT_MODEL) -> dict:
    """
    Run claude -p non-interactively and return result dict.
    Async wrapper around subprocess so FastAPI stays non-blocking.
    """
    full_prompt = _write_restriction_prefix() + prompt

    cmd = [
        CLAUDE_PATH, "-p", full_prompt,
        "--model", model,
        "--output-format", "text",
        "--allowedTools", "Read,Write,Edit,Grep,Glob,LS,Bash",
    ]

    logger.debug(f"Running claude | model={model} | prompt_len={len(full_prompt)}")
    start = datetime.now()

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(Path.home()),
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=TASK_TIMEOUT
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            logger.error("claude timed out")
            return {"success": False, "text": "Request timed out.", "duration_s": TASK_TIMEOUT}

        duration = (datetime.now() - start).total_seconds()
        output = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()

        if err:
            logger.debug(f"stderr: {err[:500]}")

        quota_kw = ["rate limit", "rate_limit", "429", "quota", "usage limit",
                    "too many requests", "capacity", "overloaded", "throttl"]
        is_quota = any(kw in (output + err).lower() for kw in quota_kw)

        if is_quota:
            logger.warning("Quota/rate-limit detected")
            return {
                "success": False,
                "text": "Claude quota limit reached. Try again in an hour.",
                "duration_s": round(duration, 1),
            }

        if proc.returncode != 0:
            logger.error(f"claude exit {proc.returncode}: {err[:300]}")
            return {
                "success": False,
                "text": f"Agent error (exit {proc.returncode}). Check logs.",
                "duration_s": round(duration, 1),
            }

        logger.info(f"claude OK | {round(duration, 1)}s | output={len(output)} chars")
        return {"success": True, "text": output, "duration_s": round(duration, 1)}

    except FileNotFoundError:
        logger.error(f"claude not found at {CLAUDE_PATH}")
        return {"success": False, "text": "claude CLI not found. Check CLAUDE_PATH in agent.py.", "duration_s": 0}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/message", response_model=MessageResponse)
async def handle_message(req: MessageRequest):
    logger.info(f"Message from user={req.user_id} | text={req.text[:100]}")
    result = await run_claude(req.text)
    return MessageResponse(
        text=result["text"],
        success=result["success"],
        duration_s=result["duration_s"],
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Jarvis agent engine starting on localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")