#!/usr/bin/env python3
"""
Claude Code Task Orchestrator
==============================
Reads task definitions from an Obsidian-compatible Markdown file with YAML
frontmatter, executes them sequentially via Claude Code's headless mode (-p),
with quota retry, scheduling, logging, and Obsidian integration.

Features:
- Per-batch curfew window in YAML frontmatter
- Checkbox status updates in source file ([ ] -> [x] or [!])
- Obsidian [[wikilink]] resolution to real file paths
- Model selection per task
- Scheduled start times per task
- Quota retry with configurable limits
- Comprehensive logging with timestamps
- Default output directory and naming
- Output verification
- Completion summary appended to task file

Setup:
    pip install pyyaml
    npm install -g @anthropic-ai/claude-code

Usage:
    python claude_orchestrator.py ~/Obsidian/claude-inbox/tonight.md
"""

import subprocess
import sys
import os
import re
import time
import json
import logging
from datetime import datetime, timedelta, time as dtime
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml")
    sys.exit(1)


# ─── Configuration Defaults ─────────────────────────────────────────────────

DEFAULT_MODEL = "sonnet"
DEFAULT_OUTPUT_DIR = None
MAX_RETRIES = 4
DEFAULT_CURFEW_END = "07:00"
TASK_TIMEOUT_SECONDS = 3600

# Default write-scoped permissions for Obsidian safety
# Read is unrestricted; Write is limited to specific directories
# Set to None to disable (Claude gets full permissions)
DEFAULT_ALLOWED_TOOLS = None  # populated from YAML frontmatter

MODELS = {
    "opus":    "claude-opus-4-6",
    "sonnet":  "claude-sonnet-4-5-20250929",
    "haiku":   "claude-haiku-4-5",
    "claude-opus-4-6":              "claude-opus-4-6",
    "claude-sonnet-4-5-20250929":   "claude-sonnet-4-5-20250929",
    "claude-haiku-4-5":             "claude-haiku-4-5",
    "opusplan": "opusplan",
}


# ─── Obsidian Wikilink Resolution ────────────────────────────────────────────

class ObsidianResolver:
    """Resolve [[wikilinks]] to real file paths within an Obsidian vault."""

    def __init__(self, vault_root: Path):
        self.vault_root = vault_root
        self._index: dict[str, Path] = {}
        self._build_index()

    def _build_index(self):
        for f in self.vault_root.rglob("*"):
            if f.is_file() and not f.name.startswith("."):
                key = f.stem.lower()
                if key not in self._index or f.suffix == ".md":
                    self._index[key] = f

    def resolve(self, link_text: str) -> Optional[str]:
        target = link_text.split("|")[0].strip()

        if "/" in target:
            for ext in ["", ".md"]:
                candidate = self.vault_root / (target + ext)
                if candidate.exists():
                    return str(candidate)

        key = target.lower()
        if key in self._index:
            return str(self._index[key])
        if key.endswith(".md") and key[:-3] in self._index:
            return str(self._index[key[:-3]])

        return None

    def resolve_in_text(self, text: str) -> str:
        def replacer(match):
            resolved = self.resolve(match.group(1))
            return resolved if resolved else f"[[{match.group(1)}]]"
        return re.sub(r"\[\[([^\]]+)\]\]", replacer, text)


# ─── Logging ─────────────────────────────────────────────────────────────────

def setup_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"orchestrator_{timestamp}.log"

    logger = logging.getLogger("orchestrator")
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(asctime)s | %(message)s", datefmt="%H:%M:%S"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.info(f"Log file: {log_file}")
    return logger


# ─── Task File Status Updates ────────────────────────────────────────────────

def update_checkbox(filepath: Path, task_name: str, success: bool):
    """- [ ] Task  ->  - [x] Task (success) or - [!] Task (failed)"""
    content = filepath.read_text(encoding="utf-8")
    escaped = re.escape(task_name)
    new_mark = "[x]" if success else "[!]"
    updated = re.sub(
        rf"(- \[[ ]\])\s*{escaped}",
        f"- {new_mark} {task_name}",
        content, count=1
    )
    if updated != content:
        filepath.write_text(updated, encoding="utf-8")


def append_completion_summary(filepath: Path, results: list[dict]):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"\n\n---\n## Orchestrator Run: {timestamp}\n"]
    for r in results:
        # Build Obsidian wikilink to output file if it exists
        output_link = ""
        if r.get("output"):
            output_name = Path(r["output"]).stem
            output_link = f" → [[{output_name}]]"

        if r.get("skipped"):
            lines.append(f"- ⏭️ **{r['task']}** — skipped (curfew)")
        elif r.get("success"):
            lines.append(
                f"- ✅ **{r['task']}** — "
                f"{r.get('attempts', '?')} attempt(s), {r.get('duration_s', 0)}s{output_link}"
            )
        else:
            lines.append(
                f"- ❌ **{r['task']}** — "
                f"{r.get('attempts', '?')} attempt(s), {r.get('duration_s', 0)}s"
            )

    content = filepath.read_text(encoding="utf-8")
    content += "\n".join(lines) + "\n"
    filepath.write_text(content, encoding="utf-8")


# ─── Task Parsing ────────────────────────────────────────────────────────────

def parse_time_str(time_str: str) -> dtime:
    parts = time_str.strip().split(":")
    return dtime(int(parts[0]), int(parts[1]))


def parse_tasks_file(filepath: Path, resolver: Optional[ObsidianResolver] = None):
    """
    Parse task file. Supports two formats:

    FORMAT A — Sectioned (## Task: Name):
        ## Task: Research Topic
        - model: opus
        - output: ~/path/output.md
        Detailed prompt...

    FORMAT B — Flat checklist:
        - [ ] Prompt text here
        - [ ] Another task {model: opus, output: ~/path.md}

    Returns: (config_dict, task_list)
    """
    content = filepath.read_text(encoding="utf-8")

    frontmatter = {}
    body = content
    fm_match = re.match(r"^---\s*\n(.+?)\n---\s*\n", content, re.DOTALL)
    if fm_match:
        frontmatter = yaml.safe_load(fm_match.group(1)) or {}
        body = content[fm_match.end():]

    config = {
        "default_model": frontmatter.get("default_model", DEFAULT_MODEL),
        "default_output_dir": frontmatter.get("default_output_dir", None),
        "curfew": frontmatter.get("curfew", DEFAULT_CURFEW_END),
        "max_retries": int(frontmatter.get("retry", MAX_RETRIES)),
        "write_dirs": frontmatter.get("write_dirs", None),
    }

    has_sections = bool(re.search(r"^##\s+Task:", body, re.MULTILINE))

    if has_sections:
        tasks = _parse_sectioned(body, config, resolver)
    else:
        tasks = _parse_flat(body, config, resolver)

    return config, tasks


def _parse_sectioned(body, config, resolver):
    sections = re.split(r"^##\s+Task:\s*", body, flags=re.MULTILINE)
    tasks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue

        lines = section.split("\n")
        task_name = lines[0].strip()
        metadata, prompt_lines = {}, []
        in_meta = True

        for line in lines[1:]:
            s = line.strip()
            if in_meta and s.startswith("- ") and ":" in s and not s.startswith("- ["):
                k, _, v = s[2:].partition(":")
                metadata[k.strip()] = v.strip()
            else:
                in_meta = False
                prompt_lines.append(line)

        prompt = "\n".join(prompt_lines).strip()
        if not prompt:
            continue
        if resolver:
            prompt = resolver.resolve_in_text(prompt)

        tasks.append(_build_task(task_name, prompt, metadata, config))
    return tasks


def _parse_flat(body, config, resolver):
    tasks = []
    for match in re.finditer(r"^- \[[ ]\]\s*(.+)", body, re.MULTILINE):
        raw = match.group(1).strip()
        metadata, prompt = {}, raw

        # Inline metadata: {model: opus, output: ~/path.md}
        meta_match = re.search(r"\{(.+?)\}\s*$", raw)
        if meta_match:
            prompt = raw[:meta_match.start()].strip()
            for pair in meta_match.group(1).split(","):
                if ":" in pair:
                    k, _, v = pair.partition(":")
                    metadata[k.strip()] = v.strip()

        task_name = prompt[:80].rstrip()
        if len(prompt) > 80:
            task_name += "..."

        if resolver:
            prompt = resolver.resolve_in_text(prompt)

        tasks.append(_build_task(task_name, prompt, metadata, config))
    return tasks


def _build_task(name, prompt, metadata, config):
    model_key = metadata.get("model", config["default_model"]).lower()
    model = MODELS.get(model_key, model_key)

    output = metadata.get("output")
    if not output:
        safe = re.sub(r"[^\w\-]", "-", name.lower()).strip("-")
        # Collapse runs of dashes and trim to readable length
        safe = re.sub(r"-{2,}", "-", safe)[:60].rstrip("-")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ts}-{safe}.md"
        base = config.get("default_output_dir") or str(Path.home() / "claude-output")
        output = str(Path(base).expanduser() / filename)
    output = str(Path(output).expanduser())

    schedule = None
    if "schedule" in metadata:
        try:
            schedule = datetime.strptime(metadata["schedule"], "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                t = datetime.strptime(metadata["schedule"], "%H:%M")
                now = datetime.now()
                schedule = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
                if schedule < now:
                    schedule += timedelta(days=1)
            except ValueError:
                pass

    return {
        "name": name,
        "prompt": prompt,
        "model": model,
        "output": output,
        "schedule": schedule,
        "max_retries": int(metadata.get("retry", config.get("max_retries", MAX_RETRIES))),
    }


# ─── Execution ───────────────────────────────────────────────────────────────

def is_within_curfew(curfew_end: str) -> bool:
    end = parse_time_str(curfew_end)
    now = datetime.now().time()
    return now < end


def wait_until_next_hour(logger):
    now = datetime.now()
    next_hour = (now + timedelta(hours=1)).replace(minute=1, second=0, microsecond=0)
    wait_secs = (next_hour - now).total_seconds()
    logger.info(f"Waiting until {next_hour.strftime('%H:%M')} ({int(wait_secs)}s)...")
    time.sleep(wait_secs)


def wait_until_schedule(schedule, logger):
    now = datetime.now()
    if schedule > now:
        secs = (schedule - now).total_seconds()
        logger.info(f"Scheduled: {schedule.strftime('%Y-%m-%d %H:%M')} (waiting {int(secs)}s)")
        time.sleep(secs)


def build_write_restriction_prompt(write_dirs: list[str], task_output: str) -> str:
    """
    Build a prompt prefix instructing Claude to only write to allowed directories.
    Claude Code's --allowedTools does not support path-scoped Write(path/*) globs,
    so we enforce write restrictions via prompt instructions instead.
    """
    expanded = [str(Path(d).expanduser()).rstrip("/") for d in write_dirs]
    output_dir = str(Path(task_output).parent)
    if output_dir not in expanded:
        expanded.append(output_dir)
    dirs_list = "\n".join(f"  - {d}" for d in expanded)
    return (
        f"IMPORTANT: You may only write or edit files in these directories:\n"
        f"{dirs_list}\n"
        f"Do NOT write to any other location.\n\n"
    )


def run_claude_task(task, write_dirs, logger):
    output_path = Path(task["output"])
    output_path.parent.mkdir(parents=True, exist_ok=True)

    prompt = task["prompt"]
    if task["output"] not in prompt:
        prompt += f"\n\nWrite your output to: {task['output']}"

    # Add prompt-level write restrictions if configured
    if write_dirs:
        prompt = build_write_restriction_prompt(write_dirs, task["output"]) + prompt

    # --allowedTools with bare tool names pre-authorises all tools so Claude
    # doesn't prompt for interactive approval in -p mode. Path-scoped globs
    # like Write(/path/*) are NOT supported by Claude Code CLI.
    # Write safety is enforced via prompt instructions above.
    cmd = ["claude", "-p", prompt, "--model", task["model"], "--output-format", "text",
           "--allowedTools", "Read,Write,Edit,Grep,Glob,LS,Bash"]

    if write_dirs:
        logger.debug(f"Write dirs (prompt-enforced): {write_dirs}")
    else:
        logger.debug("Write permissions: unrestricted")
    logger.debug(f"Model: {task['model']}")
    logger.debug(f"Output: {task['output']}")
    logger.debug(f"Prompt: {len(prompt)} chars")

    start = datetime.now()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=TASK_TIMEOUT_SECONDS, cwd=str(Path.home()),
        )
        duration = (datetime.now() - start).total_seconds()

        combined = (result.stdout + result.stderr).lower()
        quota_kw = ["rate limit", "rate_limit", "429", "quota", "usage limit",
                     "too many requests", "capacity", "overloaded", "throttl"]
        is_quota = any(kw in combined for kw in quota_kw)
        verified = output_path.exists() and output_path.stat().st_size > 0
        success = result.returncode == 0 and not is_quota

        # Require output file to exist — exit 0 without a file is a Claude failure
        if success and not verified:
            logger.warning(f"Exit 0 but output file not found: {output_path}")
            success = False

        return {
            "success": success,          # use the variable, not recomputed expression
            "is_quota_error": is_quota,
            "exit_code": result.returncode,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-2000:] if result.stderr else "",
            "duration_s": round(duration, 1),
            "output_verified": verified,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "is_quota_error": False, "exit_code": -1,
                "stdout": "", "stderr": "TIMEOUT", "duration_s": round(
                    (datetime.now() - start).total_seconds(), 1), "output_verified": False}
    except FileNotFoundError:
        return {"success": False, "is_quota_error": False, "exit_code": -2,
                "stdout": "", "stderr": "'claude' not found",
                "duration_s": 0, "output_verified": False}


def execute_with_retry(task, curfew_end, write_dirs, logger):
    if task.get("schedule"):
        wait_until_schedule(task["schedule"], logger)

    result = {}
    for attempt in range(1, task["max_retries"] + 1):
        logger.info(f"[{task['name']}] Attempt {attempt}/{task['max_retries']} ({task['model']})")
        result = run_claude_task(task, write_dirs, logger)

        if result["success"]:
            tag = "✅ VERIFIED" if result["output_verified"] else "⚠️ done, output not found"
            logger.info(f"[{task['name']}] {tag} ({result['duration_s']}s)")
            return {**result, "attempts": attempt, "output": task["output"]}

        if result["is_quota_error"]:
            logger.warning(f"[{task['name']}] Quota hit (attempt {attempt})")
            if attempt >= task["max_retries"]:
                logger.error(f"[{task['name']}] Retries exhausted")
                return {**result, "attempts": attempt, "output": task["output"]}
            if not is_within_curfew(curfew_end):
                logger.warning(f"[{task['name']}] Past curfew ({curfew_end}). Stopping.")
                return {**result, "attempts": attempt, "output": task["output"],
                        "stopped_by_curfew": True}
            wait_until_next_hour(logger)
            continue

        logger.error(f"[{task['name']}] Failed (exit {result['exit_code']}): "
                     f"{result['stderr'][:500]}")

        # Retry if Claude ran but didn't write the output file
        if not result["output_verified"] and attempt < task["max_retries"]:
            logger.warning(f"[{task['name']}] No output file — retrying")
            continue

        return {**result, "attempts": attempt, "output": task["output"]}

    return {**result, "attempts": task["max_retries"], "output": task["output"]}


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python claude_orchestrator.py <tasks.md>")
        print("  e.g. python claude_orchestrator.py ~/Obsidian/claude-inbox/tonight.md")
        sys.exit(1)

    tasks_file = Path(sys.argv[1]).expanduser()
    if not tasks_file.exists():
        print(f"ERROR: Not found: {tasks_file}")
        sys.exit(1)

    # Find Obsidian vault root
    vault_root = None
    check = tasks_file.parent
    for _ in range(10):
        if (check / ".obsidian").exists():
            vault_root = check
            break
        if check == check.parent:
            break
        check = check.parent

    resolver = ObsidianResolver(vault_root) if vault_root else None

    # Logging directory
    log_dir = tasks_file.parent / ".claude-logs"
    if vault_root:
        candidate = vault_root / "claude" / "claude-logs"
        if candidate.parent.exists():
            log_dir = candidate

    logger = setup_logging(log_dir)
    logger.info("=" * 60)
    logger.info("Claude Code Orchestrator")
    logger.info(f"Tasks: {tasks_file}")
    if vault_root:
        logger.info(f"Vault: {vault_root}")
        logger.info(f"Wikilinks: {len(resolver._index)} files indexed")
    logger.info("=" * 60)

    config, tasks = parse_tasks_file(tasks_file, resolver)
    if not tasks:
        logger.error("No tasks found.")
        sys.exit(1)

    curfew = config["curfew"]
    write_dirs = config.get("write_dirs")
    logger.info(f"Curfew: {curfew} | Default model: {config['default_model']}")
    if write_dirs:
        logger.info(f"Write restricted to: {write_dirs}")
    else:
        logger.info("Write permissions: unrestricted (add write_dirs to YAML to restrict)")
    logger.info(f"{len(tasks)} task(s):")
    for i, t in enumerate(tasks, 1):
        s = t["schedule"].strftime("%H:%M") if t["schedule"] else "now"
        logger.info(f"  {i}. {t['name']} [{t['model']}] @ {s}")

    results = []
    for i, task in enumerate(tasks, 1):
        logger.info(f"\n{'─' * 60}")
        logger.info(f"Task {i}/{len(tasks)}: {task['name']}")
        logger.info(f"{'─' * 60}")

        result = execute_with_retry(task, curfew, write_dirs, logger)
        results.append({"task": task["name"], **result})
        update_checkbox(tasks_file, task["name"], result.get("success", False))

        if result.get("stopped_by_curfew"):
            remaining = len(tasks) - i
            if remaining > 0:
                logger.warning(f"Curfew. Skipping {remaining} task(s).")
                for j in range(i, len(tasks)):
                    results.append({"task": tasks[j]["name"], "success": False,
                                    "attempts": 0, "duration_s": 0, "skipped": True})
            break

    # Summary
    logger.info(f"\n{'=' * 60}")
    logger.info("SUMMARY")
    logger.info(f"{'=' * 60}")

    ok = sum(1 for r in results if r.get("success"))
    total_t = sum(r.get("duration_s", 0) for r in results)

    for r in results:
        if r.get("skipped"):
            logger.info(f"  ⏭️  {r['task']} — skipped")
        elif r.get("success"):
            v = " ✓" if r.get("output_verified") else ""
            logger.info(f"  ✅ {r['task']} — {r['attempts']}x, {r['duration_s']}s{v}")
        else:
            logger.info(f"  ❌ {r['task']} — {r.get('attempts', '?')}x, {r.get('duration_s', 0)}s")

    logger.info(f"\n{ok}/{len(results)} succeeded | {round(total_t / 60, 1)} min total")

    append_completion_summary(tasks_file, results)
    sys.exit(0 if ok == len(results) else 1)


if __name__ == "__main__":
    main()
