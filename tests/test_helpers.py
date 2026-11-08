import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from jarvis.helpers import chunk_text, is_quota_error  # noqa: E402


# ── is_quota_error ────────────────────────────────────────────────────────────

def test_successful_answer_mentioning_quota_is_not_quota_error():
    assert not is_quota_error("", "Your API quota is 429 requests per capacity unit", 0)


def test_stderr_rate_limit_detected():
    assert is_quota_error("Error: rate limit exceeded", "", 1)


def test_stdout_checked_only_when_failed_and_stderr_empty():
    assert is_quota_error("", "usage limit reached", 1)
    assert not is_quota_error("some unrelated error", "usage limit reached", 1)


def test_plain_failure_is_not_quota():
    assert not is_quota_error("segfault", "", 2)


# ── chunk_text ────────────────────────────────────────────────────────────────

def test_empty_text_gives_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n ") == []


def test_short_text_single_chunk():
    assert chunk_text("hello") == ["hello"]


def test_splits_on_line_boundaries_within_limit():
    text = "\n".join(["x" * 50] * 10)
    chunks = chunk_text(text, max_len=120)
    assert all(len(c) <= 120 for c in chunks)
    assert "\n".join(chunks) == text


def test_long_single_line_is_hard_split_without_empty_chunks():
    text = "a" * 9000
    chunks = chunk_text(text, max_len=4000)
    assert all(c and len(c) <= 4000 for c in chunks)
    assert "".join(chunks) == text


def test_first_line_longer_than_limit_does_not_emit_empty_chunk():
    text = "b" * 300 + "\nshort"
    chunks = chunk_text(text, max_len=100)
    assert all(c.strip() for c in chunks)
    assert "".join(chunks).replace("\n", "") == "b" * 300 + "short"
