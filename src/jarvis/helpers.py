"""
jarvis.helpers
==============
Pure helper functions with no third-party dependencies, so they can be
unit-tested without FastAPI, httpx, or python-telegram-bot installed.
"""

from typing import Optional

TELEGRAM_MAX_LEN = 4000  # Telegram's hard limit is 4096; keep headroom.

_QUOTA_KEYWORDS = (
    "rate limit", "rate_limit", "429", "quota", "usage limit",
    "too many requests", "capacity", "overloaded", "throttl",
)


def is_quota_error(stderr: str, stdout: str, returncode: Optional[int]) -> bool:
    """
    Decide whether a claude subprocess failed because of quota/rate limiting.

    A successful run (returncode 0) is never a quota error, no matter what the
    response text says: an answer that merely mentions "quota", "capacity" or
    "429" must not be replaced with a quota-limit message. stderr is checked
    first as the authoritative source; stdout is consulted only for a failed
    run whose stderr is empty.
    """
    if returncode == 0:
        return False
    err = stderr.lower()
    if any(kw in err for kw in _QUOTA_KEYWORDS):
        return True
    if not err.strip():
        out = stdout.lower()
        return any(kw in out for kw in _QUOTA_KEYWORDS)
    return False


def chunk_text(text: str, max_len: int = TELEGRAM_MAX_LEN) -> list[str]:
    """
    Split text into chunks of at most max_len characters, preferring line
    boundaries. Lines longer than max_len are hard-split. Never returns an
    empty chunk (Telegram rejects empty messages); empty input yields [].
    """
    if not text or not text.strip():
        return []
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if current:
            chunks.append("\n".join(current))
        current, current_len = [], 0

    for line in text.split("\n"):
        # Hard-split any single line that cannot fit in one chunk.
        while len(line) > max_len:
            flush()
            chunks.append(line[:max_len])
            line = line[max_len:]
        if current_len + len(line) + 1 > max_len:
            flush()
        current.append(line)
        current_len += len(line) + 1
    flush()

    return [c for c in chunks if c.strip()]
