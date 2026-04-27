# Jarvis — Personal AI Assistant

A personal AI assistant built on Claude Code, designed to run on your own machine and be accessible through multiple channels (Telegram, web UI, CLI, Apple Watch). Backed by multi-provider LLM execution, your Obsidian vault for persistent memory and knowledge, and local document search via LlamaIndex RAG.

Telegram is the first channel. The agent engine is the product.

---

## Architecture

```
┌──────────────────────────────────────────────┐
│               CHANNELS                       │
│                                              │
│  Telegram  │  Web UI  │  Watch  │  CLI       │
│  (mobile)  │ (desktop)│ (voice) │ (terminal) │
└─────┬──────┴────┬─────┴────┬────┴───┬────────┘
      │           │          │        │
      ▼           ▼          ▼        ▼
┌──────────────────────────────────────────────┐
│         GATEWAY / API LAYER                  │
│  (FastAPI on localhost:8000)                 │
│  - Auth per channel                          │
│  - Message normalisation (text/voice→text)   │
│  - Response formatting per channel           │
│  - Session management                        │
│  - Bot commands (/usage, /remember, /task)   │
└──────────────────┬───────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌──────────────┐  ┌───────────────────────┐
│  LLM Router  │  │  LlamaIndex RAG       │
│              │  │  (context retrieval)  │
│  claude -p   │  │                       │
│  codex -p    │  │  Ollama embeddings    │
│  gemini -p   │  │  FAISS vector store   │
│  ollama API  │  └───────────┬───────────┘
└──────┬───────┘              │
       │                      │
       ▼                      ▼
┌──────────────────────────────────────────────┐
│  DATA LAYER                                  │
│                                              │
│  Obsidian Vault (~/Obsidian)                 │
│  - Memory: jarvis-memory/ (facts + logs)     │
│  - Knowledge: all notes (indexed by RAG)     │
│  - Tasks: claude-inbox/ + claude-outbox/     │
│  - Security: .claudeignore exclusions        │
│                                              │
│  Google Services (via MCP)                   │
│  - Gmail, Calendar, Drive                    │
│                                              │
│  Batch Orchestrator                          │
│  - claude_orchestrator.py (overnight tasks)  │
└──────────────────────────────────────────────┘
```

The agent engine is a **separate local API service** — channels are thin clients. Adding a web UI or Apple Watch app later just requires a new client calling the same `localhost:8000` endpoint.

---

## What's in This Repo

### `jarvis/`
The Python package containing all service code.

**`jarvis/agent.py`** — FastAPI agent engine on `localhost:8000`. All LLM execution lives here. Channels are thin clients that call this service. Features:
- `claude -p` subprocess execution with async wrapper (event loop stays unblocked)
- Shared secret auth on `/message` endpoint (`JARVIS_AGENT_SECRET`)
- Hard-block prompt injection detection (6 patterns, raises HTTP 400)
- Write directory restrictions via prompt prefix (`JARVIS_WRITE_DIRS`)
- Concurrent request semaphore (one `claude -p` subprocess at a time)
- Graceful shutdown: terminates in-flight subprocesses on SIGTERM
- No `Bash` tool — interactive path has no legitimate shell need

**`jarvis/bot.py`** — Telegram bot thin client. Receives messages, forwards to agent engine, returns responses. Features:
- Allowlist auth via `TELEGRAM_ALLOWED_USERS`
- Persistent typing indicator (loops every 4s until agent responds)
- Typed exception handling for agent calls (connect error, timeout, HTTP errors)
- Telegram 4096-char chunking (line-aware)

**`jarvis/logging_config.py`** — Shared logging setup. Both services call `configure_logging(name, log_dir)` rather than duplicating handler configuration. Rotating file handler (5MB, 3 backups) + stream handler. Suppresses noisy third-party loggers.

### `run_agent.py` / `run_bot.py`
Thin entry points for launchd plists and cron. Both are one-liners that import and call `main()` from the package. Reference these paths in your launchd plists, not the files inside `jarvis/`.

### `claude_orchestrator.py`
The batch task runner. Reads task definitions from an Obsidian-compatible Markdown file with YAML frontmatter, then executes them sequentially via Claude Code's headless mode (`-p`). Features:
- Per-batch curfew window (stops retrying before morning to preserve daytime quota)
- Quota retry with hourly backoff
- Checkbox status updates in source file (`[ ]` → `[x]` or `[!]`)
- Obsidian `[[wikilink]]` resolution to real file paths
- Per-task model selection and scheduled start times
- Write directory restrictions via `--allowedTools`
- Completion summary appended to task file

### `example-tasks.md`
Sample task file showing both the flat checklist format (quick tasks) and the detailed sectioned format (complex overnight tasks with scheduling).

### `claude-code-guide.md`
Comprehensive guide to running Claude Code as an autonomous agent — models, quota management, MCP servers, subagents, cron automation, and cost optimisation.

### `templates/`
Eight reusable prompt templates:

| # | Template | Use Case |
|---|----------|----------|
| 01 | [Research Deep Dive](templates/01-research-deep-dive.md) | Web research → comprehensive report |
| 02 | [Code Spike / Prototype](templates/02-code-spike-prototype.md) | Prove out technical concepts quickly |
| 03 | [Anki Cards](templates/03-anki-cards.md) | Review existing or generate new cards |
| 04 | [File Duplicates & Organization](templates/04-file-duplicates-organization.md) | Find dupes across drives |
| 05 | [Data Analysis & Report](templates/05-data-analysis-report.md) | EDA, metrics, data quality reports |
| 06 | [Document Drafting](templates/06-document-drafting.md) | Proposals, emails, technical documents |

### `docs/scope.md`
Full project scope: vision, architecture decisions, LLM provider strategy, phased roadmap, security model, and cost analysis.

---

## Quick Start

```bash
# Prerequisites
npm install -g @anthropic-ai/claude-code   # requires Node.js 18+
pip install pyyaml fastapi uvicorn python-telegram-bot httpx
```

**First-time setup — generate and store the agent secret:**

`JARVIS_AGENT_SECRET` is a shared secret that authenticates the bot to the agent engine.
Generate it once and store the same value in both launchd plists permanently — it must
match across both services and survive restarts.

```bash
openssl rand -hex 32
# Copy the output — e.g. a3f8c2e1d9b74f2e8c3a1b5d6e9f0c7a...
# Paste this static value into both launchd plists (see launchd section below)
```

**Launchd plist `EnvironmentVariables` block (both plists get the same values):**

```xml
<key>EnvironmentVariables</key>
<dict>
    <key>TELEGRAM_BOT_TOKEN</key>
    <string>your-bot-token-from-botfather</string>
    <key>TELEGRAM_ALLOWED_USERS</key>
    <string>your-telegram-user-id</string>
    <key>JARVIS_AGENT_SECRET</key>
    <string>paste-your-generated-secret-here</string>
</dict>
```

```bash
# Run the agent engine (or via launchd: see docs/scope.md)
python run_agent.py

# Run the Telegram bot (separate terminal or launchd service)
python run_bot.py

# Run a single task headlessly (orchestrator)
claude -p "Read ~/notes/topic.md and write a report to ~/reports/output.md" --model sonnet

# Run a batch of tasks from a file overnight
python claude_orchestrator.py ~/Obsidian/claude-inbox/tonight.md
```

---

## Task File Format

```markdown
---
default_model: sonnet
default_output_dir: ~/Obsidian/claude-outbox
curfew: "07:00"
retry: 4
write_dirs:
  - ~/Obsidian/claude-outbox
  - ~/claude-output
---

## Task: Research Topic
- model: opus
- schedule: 01:00
- output: ~/Obsidian/claude-outbox/research-report.md
- retry: 4

Your detailed prompt here. Be specific about what files to read
and what the deliverable should look like.
```

See `example-tasks.md` for a full working example, and `claude-code-guide.md` for complete documentation on all options.

---

## Development Phases

| Phase | Goal | Status |
|-------|------|--------|
| 0 | Batch orchestrator + prompt templates | ✅ Done |
| 1 | Telegram ↔ agent engine (MVP) | 🔄 In progress |
| 2 | Persistent memory via Obsidian | ⏳ Planned |
| 3 | Google services via MCP (Gmail, Calendar, Drive) | ⏳ Planned |
| 4 | LlamaIndex RAG — full vault search | ⏳ Planned |
| 5 | Proactive behaviours (morning briefing, daily notes) | ⏳ Planned |
| 6 | Additional channels (web UI, Apple Watch, CLI) | ⏳ Planned |

See `docs/scope.md` for detailed phase plans.

---

## LLM Provider Strategy

| Provider | CLI | Cost | Best For |
|----------|-----|------|----------|
| Claude | `claude -p` | Subscription | Complex reasoning, coding, default |
| Gemini | `gemini -p` | Free (personal Google) | Research, summarisation, fallback |
| Codex | `codex -p` | Subscription | Code tasks |
| Ollama | REST API | Free (local) | Embeddings (RAG); offline fallback |

---

## Security Notes

- Uses `.claudeignore` to exclude sensitive vault directories from all LLM access
- Write permissions restricted via `--allowedTools` to whitelisted directories only
- Telegram bot token stored as env var, never in vault or git
- OAuth tokens for Google stored outside vault and outside git
- See `docs/scope.md` for the full security model

---

## Requirements

- macOS or Linux (Windows via WSL)
- Node.js 18+ (for Claude Code)
- Python 3.11+
- Claude Pro or Max subscription
- `pip install pyyaml`
- Obsidian (optional, but the workflow is designed around it)
