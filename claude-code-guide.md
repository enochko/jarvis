
# Claude Code Agent Guide

A comprehensive guide to running Claude Code as an autonomous agent,
covering orchestration, models, MCP, subagents, and practical workflows.

---

## Quick Start

```bash
# Install Claude Code (requires Node.js 18+)
npm install -g @anthropic-ai/claude-code

# Install orchestrator dependency
pip install pyyaml

# Run a single task
claude -p "Read ~/notes/topic.md and write a report to ~/reports/output.md" --model sonnet

# Run orchestrated tasks from a file
python claude_orchestrator.py ~/Obsidian/claude-inbox/tonight.md
python ~/claude_orchestrator.py ~/Obsidian/claude-inbox/tonight.md
```

---

## Running Multiple Agents

**Parallel:** Open multiple terminal tabs, each running a separate `claude -p "..."` command.
They share your subscription quota, so parallel = faster but burns quota faster.

**Sequential (recommended for overnight):** Use `claude_orchestrator.py` — runs tasks
one after another, handles quota exhaustion gracefully, respects your sleep schedule.

**The `-p` (or `--print`) flag** is the key. It runs Claude Code non-interactively:
it takes your prompt, executes, writes output, and exits. No human interaction needed.

---

## Model Selection

Use `--model` flag or shorthand. Available models as of February 2025:

| Shorthand | Full Model String              | Best For                           | Cost   |
|-----------|-------------------------------|------------------------------------|--------|
| `opus`    | `claude-opus-4-6`            | Complex reasoning, deep analysis,  | High   |
|           |                               | architectural decisions, reviews    |        |
| `sonnet`  | `claude-sonnet-4-5-20250929` | General development, research,     | Medium |
|           |                               | most tasks — best balance          |        |
| `haiku`   | `claude-haiku-4-5`           | Simple/fast tasks, card generation,| Low    |
|           |                               | file processing, high volume       |        |

**Cost strategy:** Use Haiku for bulk/simple tasks (Anki cards, file scanning),
Sonnet for general work, Opus for complex analysis (deep code reviews, architecture).

**Special mode — `opusplan`:** Uses Opus for planning, then Sonnet for execution.
Good for complex coding tasks where planning quality matters but execution is routine.

```bash
# Command line
claude -p "task" --model opus
claude -p "task" --model sonnet
claude -p "task" --model haiku

# In tasks.md for the orchestrator
## Task: My Task
- model: opus
```

---

## The Obsidian Inbox/Outbox Workflow

Recommended directory structure:

```
~/Obsidian/
├── claude-inbox/       # Task files for Claude to process
│   ├── tonight.md      # Tonight's batch of tasks
│   ├── research-batch.md
│   └── weekly-review.md
├── claude-outbox/      # Claude's completed outputs land here
│   ├── fabric-report.md
│   ├── anki-import.tsv
└── claude-logs/        # Auto-created by orchestrator
    └── orchestrator_20260217_233000.log
```

**Task file format** (YAML frontmatter + Markdown sections):

```markdown
---
default_model: sonnet
default_output_dir: ~/Obsidian/claude-outbox
---

## Task: My Research Task
- model: opus
- schedule: 01:00
- output: ~/Obsidian/claude-outbox/my-report.md
- retry: 3

Your detailed prompt here. Be specific about what you want,
what files to read, and what the deliverable should look like.
```

**YAML frontmatter fields:**
- `default_model:` — fallback model for tasks that don't specify one
- `default_output_dir:` — where outputs go if a task doesn't specify `output:`

**Per-task metadata:**
- `model:` — opus / sonnet / haiku (or full model string)
- `schedule:` — `HH:MM` (today/tomorrow) or `YYYY-MM-DD HH:MM`
- `output:` — full path for output file (auto-generated if omitted)
- `retry:` — max retry attempts for quota errors (default: 4)

---

## Quota Retry Logic

When Claude Code hits a subscription usage cap, the orchestrator:

1. Detects quota/rate limit errors (429, "rate limit", "usage limit", etc.)
2. Checks if current time is within retry window (**midnight to 7 AM**)
3. If within window: waits until **1 minute past the next hour**, then retries
4. If outside window (after 7 AM): stops to preserve quota for your waking hours
5. Repeats up to `retry:` times (default 4)

**Important:** Claude Code's subscription quota resets are not fully documented and
may not align perfectly with clock hours. The hourly retry is a reasonable heuristic.
Claude Code exits with a non-zero exit code on errors, and the orchestrator also
scans stdout/stderr for rate limit keywords as a belt-and-suspenders approach.

---

## Overnight Automation with Cron

```bash
# Edit your crontab
crontab -e

# Run tasks at midnight every weeknight
0 0 * * 1-5 /usr/bin/python3 ~/scripts/claude_orchestrator.py ~/Obsidian/claude-inbox/tonight.md >> ~/claude-cron.log 2>&1

# Run tasks at 11 PM on Sundays (weekly batch)
0 23 * * 0 /usr/bin/python3 ~/scripts/claude_orchestrator.py ~/Obsidian/claude-inbox/weekly-review.md >> ~/claude-cron.log 2>&1
```

---

## Key Concepts Explained

### What is "Agent" in Claude Code?

What we've been building IS an agent workflow. "Agent" just means Claude operates
autonomously — reading files, making decisions, using tools, writing output —
without human intervention at each step.

When you run `claude -p "prompt"`, Claude Code acts as an agent: it reads your
codebase, plans an approach, executes steps (file reads, web searches, code execution),
and delivers results. The `-p` flag is what makes it "headless" — no human in the loop.

### What Are Subagents?

Subagents are **specialist agents within a single Claude Code session**. They're
lighter-weight instances with their own context window, custom system prompt,
and restricted tool access.

**When they matter to you:**
- If you have a long Claude Code session and want to delegate a sub-task
  (e.g., "research this while I keep coding") without polluting the main context
- Each subagent gets a fresh context window = higher quality for focused tasks
- Up to 10 can run in parallel within one session

**How to create one** (in `~/.claude/agents/` or `.claude/agents/`):
```yaml
---
name: anki-card-maker
description: Generate Anki cards for vocabulary study
tools: Read, Write, Bash
model: haiku
---
You are an expert language teacher creating Anki cards
following Fluent Forever methodology...
```

**For your use case:** The orchestrator approach (separate tasks, separate sessions)
is simpler and more predictable than subagents. Subagents shine in interactive
sessions where you're doing complex multi-step work.

### What Are MCP Servers?

MCP (Model Context Protocol) is a standard for connecting Claude to external
tools and data sources. Think of it as a plugin system.

**Without MCP:** Claude Code can read/write files, run bash commands, and use
its built-in tools.

**With MCP:** Claude Code can also interact with GitHub, databases, Notion,
Google services, Slack, and hundreds of other systems.

**Is it useful for you as an individual user?** Yes, selectively:

| MCP Server | Use Case for You |
|------------|-----------------|
| `server-fetch` | Web fetching for research tasks |
| `server-filesystem` | Enhanced file operations |
| `server-github` | GitHub integration for code projects |
| `gmail` | Email summarization (see Chrome section below) |
| `google-calendar` | Calendar queries |
| `server-memory` | Persistent memory across sessions |

**Setup example:**
```bash
# Add a web fetch MCP server
claude mcp add --transport stdio fetch npx @anthropic-ai/server-fetch

# Add GitHub (needs personal access token)
claude mcp add --transport http github https://api.githubcopilot.com/mcp \
  -H "Authorization: Bearer YOUR_GITHUB_PAT"
```

### What Are Plugins?

Plugins bundle MCP servers, subagents, commands, and configuration into
installable packages. They're the packaging layer on top of everything else.
Still relatively new — most useful for team standardisation.

---

## Chrome Integration (Beta)

Claude Code has Chrome integration that lets it control your browser.
This is useful for:

**Authenticated services (login required):**
- Gmail — summarize emails, draft replies
- Google Calendar — read schedule, check conflicts
- Internal dashboards behind SSO
- Any web app where you're logged in

**Why Chrome vs direct web access:**
Claude Code CAN access the open web directly (via web search and fetch tools).
Chrome is specifically for when **authentication is required** — Claude uses
your logged-in browser session to access sites that need your credentials.

**For your use cases:**
- Gmail summaries: YES, useful via Chrome (requires your login session)
- Google Calendar: YES, useful via Chrome
- General web research: NO need for Chrome — use built-in web search
- Scraping public websites: NO need for Chrome — use built-in tools

---

## Anki Cards with Images

Your idea of a two-phase approach is correct and smart:

**Phase 1: Generate cards** (fast, cheap with Haiku)
```
## Task: Anki Cards
- model: haiku

Read lesson notes and generate TSV cards...
```

**Phase 2: Find images for cards** (separate task, uses more resources)
```
## Task: Find Images for Vocab
- model: sonnet

Read the Anki cards in ~/anki/import.tsv.
For each vocabulary word, search the web for a relevant,
clear image that illustrates the meaning.

Download images to ~/anki/images/ named by the vocabulary word.
Update the TSV to include an image column with the file path.

Skip abstract concepts that don't have clear visual representations.
Limit to 20 images per run to manage usage.
```

**Why split:**
- Card generation is cheap (text only, Haiku)
- Image search requires web access and is slower/costlier
- You can review cards first, then only fetch images for keepers
- Avoids wasting tokens on images for cards you might edit or delete

**Note on image recognition:** Claude Code can search for and download images.
Adding images directly to Anki's media folder and updating cards is doable
but requires understanding Anki's file structure. The simplest approach is
to generate a TSV with image filenames, then import both into Anki.

---

## File Duplicate Detection Across External Drives

Yes, Claude Code can traverse external drives. It runs with your user permissions.

**macOS paths:** `/Volumes/DriveName/`
**Linux paths:** `/mnt/` or `/media/username/`
**Windows (WSL):** `/mnt/c/`, `/mnt/d/`

**Content-based detection (SHA-256)** catches renamed duplicates. Same-content files with different names will be caught.

**Cross-format consideration:** `.mp3` and `.flac` of the same song have different
content hashes (different encodings). If you want cross-format detection, you'd
need audio fingerprinting — possible but more complex. Mention this in your prompt
and Claude Code can use tools like `chromaprint`/`fpcalc` if installed.

---

## Output Verification

The orchestrator checks that the output file:
1. Exists at the specified path
2. Has non-zero file size

This is a basic check. For more thorough verification, you could extend the
orchestrator or add a follow-up "review" task:

```markdown
## Task: Verify Previous Outputs
- model: haiku

Check the following files exist and contain substantive content:
- ~/Obsidian/claude-outbox/fabric-report.md (expect >1000 words)
- ~/anki/import.tsv (expect >20 rows)

Write a brief verification report to ~/Obsidian/claude-outbox/verification.md.
```

---

## Cost Optimization Tips

1. **Use Haiku for simple tasks** — Anki cards, file scanning, formatting
2. **Use Sonnet for general work** — research, coding, most reports
3. **Reserve Opus for complex reasoning** — deep code reviews, architecture decisions
4. **Split large tasks** — research + write is cheaper as two tasks than one massive prompt
5. **Run overnight** — you're not competing with your own daytime usage
6. **Batch related tasks** — one session reading multiple files is cheaper than
   separate sessions each loading the same codebase
