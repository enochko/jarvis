#!/usr/bin/env python3
"""
jarvis.agent — Jarvis Agent Engine
=====================================
FastAPI service on localhost:8000.
All LLM logic lives here — channels are thin clients.

Environment variables:
    CLAUDE_PATH            Path to claude binary (default: auto-detected via shutil.which)
    JARVIS_DEFAULT_MODEL   LLM model shorthand (default: sonnet)
    JARVIS_TASK_TIMEOUT    Subprocess timeout in seconds (default: 120)
    JARVIS_WRITE_DIRS      Comma-separated list of allowed write directories
    JARVIS_AGENT_SECRET    Shared secret for /message endpoint auth (optional but recommended)
"""

import asyncio
import os
import re
import secrets as _secrets
import shutil
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from jarvis.logging_config import configure_logging

# ── Config ────────────────────────────────────────────────────────────────────

LOG_DIR = Path("~/Obsidian/aaa-claude/jarvis-logs").expanduser()

CLAUDE_PATH = shutil.which("claude") or os.environ.get("CLAUDE_PATH", "claude")

DEFAULT_MODEL = os.environ.get("JARVIS_DEFAULT_MODEL", "sonnet")

TASK_TIMEOUT = int(os.environ.get("JARVIS_TASK_TIMEOUT", "120"))

WRITE_DIRS = [
    d.strip()
    for d in os.environ.get(
        "JARVIS_WRITE_DIRS",
        "~/Obsidian/aaa-claude/claude-outbox,~/Obsidian/aaa-claude/jarvis-memory",
    ).split(",")
]

AGENT_SECRET = os.environ.get("JARVIS_AGENT_SECRET", "")

# ── Logging ───────────────────────────────────────────────────────────────────

logger = configure_logging("agent", LOG_DIR)

# ── Injection detection ───────────────────────────────────────────────────────

_INJECTION_PATTERNS = [
    r"ignore\s+(previous|above|all)\s+instructions",
    r"new\s+instructions\s*:",
    r"\[SYSTEM\]",
    r"<\|im_start\|>",
    r"you\s+are\s+now\s+",
    r"disregard\s+(all|previous|your)",
]


def _check_injection(text: str) -> None:
    """
    Hard-block messages matching known prompt injection patterns.
    Raises HTTPException(400) on match.

    Logs up to 200 chars of message content on a match. This is a deliberate
    exception to the normal 'log length only' rule — security events warrant
    full context for forensic review (BR-008 carve-out).
    """
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(
                f"Prompt injection blocked | pattern={pattern!r} | text={text[:200]!r}"
            )
            raise HTTPException(
                status_code=400,
                detail="Message blocked: matched prompt injection pattern.",
            )


# ── Auth ──────────────────────────────────────────────────────────────────────

async def _verify_secret(x_jarvis_secret: str = Header(default="")) -> None:
    """Dependency: validate shared secret header if JARVIS_AGENT_SECRET is set."""
    if AGENT_SECRET and not _secrets.compare_digest(x_jarvis_secret, AGENT_SECRET):
        logger.warning("Rejected request with invalid agent secret")
        raise HTTPException(status_code=403, detail="Forbidden")


# ── Subprocess tracking (for graceful shutdown) ───────────────────────────────

_active_procs: list[asyncio.subprocess.Process] = []

# One Claude subprocess at a time — prevents quota double-spend on concurrent messages
_claude_semaphore = asyncio.Semaphore(1)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup checks
    if not AGENT_SECRET:
        logger.warning(
            "JARVIS_AGENT_SECRET is not set — /message endpoint has no auth. "
            "Set this before enabling Tailscale access."
        )
    claude_resolved = shutil.which(CLAUDE_PATH) or Path(CLAUDE_PATH).exists()
    if not claude_resolved:
        logger.warning(
            f"claude binary not found at '{CLAUDE_PATH}' — all requests will fail. "
            "Install Claude Code or set CLAUDE_PATH."
        )
    else:
        logger.info(f"claude binary: {CLAUDE_PATH}")

    yield

    # Shutdown: terminate any in-flight claude subprocesses and await exit.
    # Awaiting with a timeout ensures the process is truly gone before launchd
    # considers the service stopped, avoiding zombie processes.
    for proc in list(_active_procs):
        try:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
                logger.info(f"claude subprocess PID {proc.pid} terminated cleanly")
            except asyncio.TimeoutError:
                proc.kill()
                logger.warning(f"claude subprocess PID {proc.pid} killed after timeout")
        except ProcessLookupError:
            pass


# ── FastAPI ───────────────────────────────────────────────────────────────────

app = FastAPI(title="Jarvis Agent Engine", version="0.2.0", lifespan=lifespan)


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
    """
    Prompt-level write restriction injected before every user message.
    Note: this is a prompt instruction, not a system-level enforcement.
    --allowedTools restricts tool types; path scoping is not supported by Claude Code CLI.
    """
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
    Serialised via _claude_semaphore — one subprocess at a time.
    """
    full_prompt = _write_restriction_prefix() + prompt

    cmd = [
        CLAUDE_PATH, "-p", full_prompt,
        "--model", model,
        "--output-format", "text",
        # No Bash: interactive path has no legitimate shell need.
        # The batch orchestrator (claude_orchestrator.py) enables Bash separately for overnight tasks.
        "--allowedTools", "Read,Write,Edit,Grep,Glob,LS",
    ]

    async with _claude_semaphore:
        logger.debug(f"Claude semaphore acquired | model={model} | prompt_len={len(full_prompt)}")
        start = datetime.now()

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(Path.home()),
            )
            _active_procs.append(proc)

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=TASK_TIMEOUT
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                logger.error(f"claude timed out after {TASK_TIMEOUT}s")
                return {
                    "success": False,
                    "text": "Request timed out.",
                    "duration_s": float(TASK_TIMEOUT),
                }
            finally:
                try:
                    _active_procs.remove(proc)
                except ValueError:
                    pass

            duration = (datetime.now() - start).total_seconds()
            output = stdout.decode("utf-8", errors="replace").strip()
            err = stderr.decode("utf-8", errors="replace").strip()

            if err:
                logger.debug(f"stderr: {err[:500]}")

            quota_kw = [
                "rate limit", "rate_limit", "429", "quota", "usage limit",
                "too many requests", "capacity", "overloaded", "throttl",
            ]
            # Check stderr first (authoritative); only check stdout if stderr is clean.
            # Avoids false positives when Claude's response text discusses rate limiting.
            err_lower = err.lower()
            out_lower = output.lower() if not err_lower.strip() else ""
            is_quota = any(kw in err_lower or kw in out_lower for kw in quota_kw)

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
            logger.error(f"claude not found at '{CLAUDE_PATH}'. Install Claude Code or set CLAUDE_PATH.")
            return {
                "success": False,
                "text": "claude CLI not found. Check CLAUDE_PATH.",
                "duration_s": 0.0,
            }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/message", response_model=MessageResponse, dependencies=[Depends(_verify_secret)])
async def handle_message(req: MessageRequest):
    # Log message length only — never log message content (may contain Finance/Health data).
    # Exception: _check_injection logs up to 200 chars on a security event (see its docstring).
    logger.info(f"Message from user={req.user_id} | len={len(req.text)} chars")
    _check_injection(req.text)
    result = await run_claude(req.text)
    return MessageResponse(
        text=result["text"],
        success=result["success"],
        duration_s=result["duration_s"],
    )


# ── Entry point (direct execution) ───────────────────────────────────────────

def main():
    logger.info("Jarvis agent engine starting on localhost:8000")
    uvicorn.run(
        "jarvis.agent:app",
        host="127.0.0.1",
        port=8000,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
