# CLAUDE.md — Project Jarvis

**Repo:** jarvis  
**Last updated:** March 2026  
**Maintained by:** Enoch Ko  
**Version:** 0.2

---

## Project Purpose

Personal AI assistant running on macOS, accessible through multiple channels
(Telegram first, then web UI, Apple Watch, CLI). Routes messages through a
local FastAPI gateway to multiple LLM providers (Claude, Gemini, Ollama),
with persistent memory via an Obsidian vault and document retrieval via
LlamaIndex RAG.

Portfolio piece demonstrating agentic AI architecture, async Python, and
multi-provider LLM orchestration.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent engine | Python 3.11, FastAPI (async) |
| Telegram channel | `python-telegram-bot` |
| LLM providers | Claude Code CLI (`claude -p`), Gemini CLI, Ollama REST API |
| Memory / knowledge | Obsidian vault (Markdown files) |
| Document retrieval | LlamaIndex, FAISS, Ollama (`nomic-embed-text` embeddings) |
| Runtime | Conda env `jarvis`; Node.js via Homebrew for CLI tools |
| Daemon | `launchd` plist on macOS |

---

## Repository Structure

```
/
├── CLAUDE.md                    ← This file
├── claude_orchestrator.py       ← Batch task runner (operational)
├── example-tasks.md             ← Sample task file with YAML frontmatter
├── README.md                    ← Project overview
├── docs/
│   ├── scope.md                 ← Architecture, phases, action items
│   ├── jarvis-ideas.md          ← Ideas backlog with prioritisation
│   └── claude-code-guide.md     ← Claude Code agent workflow reference
└── templates/                   ← Prompt templates (01–08)
```

---

## Architecture Principles — DO NOT VIOLATE

**Agent engine is separate from channels.** Channels are thin clients calling
`localhost:8000`. Never embed LLM logic directly in a channel handler.
Adding a new channel = new client only; agent engine stays unchanged.

**Passive signals never trigger LLM calls.** Only explicit user messages
trigger agent execution. Background events (file changes, cron ticks) trigger
pre-defined workflows, not open-ended LLM invocations.

**Write restrictions are always enforced.** The orchestrator's `write_dirs`
whitelist and `--allowedTools` restrictions must be present for all overnight
tasks. Never suggest removing write restrictions for unattended runs.

**Memory is Obsidian files.** Conversation logs and facts live in
`~/Obsidian/aaa-claude/jarvis-memory/`. Context injection is ~1-2KB per query
(facts + recent summaries), not the whole vault.

**Sensitive data stays local.** Finance, health, and personal document
collections are processed via Ollama only — never routed through cloud LLMs.
`.claudeignore` exclusions enforce this at the file level.

---

## Invariants / Business Rules

| Rule | Summary |
|---|---|
| BR-001 | Agent engine handles all LLM logic. Channels are thin clients only. |
| BR-002 | Passive signals (file changes, cron) never trigger open-ended LLM calls. |
| BR-003 | All overnight tasks must have a curfew check and a maximum retry ceiling. |
| BR-004 | Write operations are restricted to `write_dirs` whitelist at all times. |
| BR-005 | Output verification required: file must exist and be non-empty before marking success. |
| BR-006 | Credentials never in the vault or in git. Use env vars. |
| BR-007 | `.claudeignore` exclusions apply to Claude Code reads, LlamaIndex indexing, and Ollama. |
| BR-008 | Finance, health, and personal documents: Ollama/local pipeline only. No cloud LLM. |
| BR-009 | Obsidian outputs must be valid Markdown with YAML frontmatter (`date created`, `source: jarvis`). |
| BR-010 | Context injection is bounded: ~1-2KB facts + recent summaries. Never send the full vault. |

---

## LLM Routing

| Use case | Provider | Rationale |
|---|---|---|
| Default / general | Claude Sonnet | Best balance of quality and quota |
| Complex reasoning, architecture | Claude Opus | Reserved; use sparingly |
| High-volume simple tasks | Claude Haiku | Cheap, fast |
| Web research, summarisation | Gemini | Free with personal Google account |
| Local embeddings | Ollama `nomic-embed-text` | Free, private, no data leaves device |
| Sensitive content classification | Ollama vision model | Local-only requirement |
| Fallback (quota exhausted) | Gemini first, then Ollama | Gemini faster/better; Ollama offline only |

---

## Code Conventions

**Async everywhere.** Use `async`/`await` throughout the agent engine and bot
handlers. The orchestrator uses subprocess, which is intentional for CLI isolation.

**Idempotent operations.** File writes must be safe to retry. Task state is
tracked via checkbox updates in the source Markdown (`[ ]` → `[x]` or `[!]`).

**Retry and failure states.** Every external call (LLM, Google API, Telegram)
needs explicit retry logic with exponential backoff or hour-boundary waiting.
Log quota errors, timeouts, and non-zero exit codes separately — they have
different recovery paths.

**Logging.** Python `logging` with timestamps. File handler at DEBUG, stream
handler at INFO. Log to `~/Obsidian/aaa-claude/jarvis-logs/` with
`YYYYMMDD_HHMMSS` prefix.

**Python style.** Type hints on all function signatures. `Path` over string
paths. `Optional[X]` over `X | None` for 3.11 compatibility.

**Conda/pip discipline.** All application packages installed via pip inside the
`jarvis` conda env. Never `pip install --upgrade` broadly inside a conda env.
Use absolute Python path in launchd plists (`conda run -n jarvis which python`).

---

## Overnight Run Risk Flags

Always flag these explicitly when suggesting code or tasks:

- **Unrecoverable file mutations** — writes outside `write_dirs` without a backup step.
- **Unbounded API loops** — retry logic without a ceiling or curfew check.
- **Cost blow-out** — Opus or repeated Sonnet in loops where Haiku/Gemini suffice.
- **Missing output verification** — success claimed without checking file exists and is non-empty.
- **Sensitive data to cloud LLM** — any Finance/Health content routed outside Ollama.

---

## DO

- Use `claude -p` (Claude Code headless) for all agent LLM execution
- Enforce `write_dirs` and curfew checks on all overnight tasks
- Verify output file exists and is non-empty before marking a task successful
- Use `async`/`await` throughout agent engine and channel handlers
- Keep the agent engine stateless per request; persist state to Obsidian files
- Check `docs/scope.md` open questions before implementing new integrations
- Use Gemini for bulk/research tasks to preserve Claude quota
- When producing files for the repo, always append `git add` and `git commit` commands at the end of the response, using chained `-m` flags for multi-line commits

## DON'T

- Don't embed LLM logic in channel handlers — route through the agent engine
- Don't send Finance, Health, or personal document content to cloud LLMs
- Don't run overnight tasks without a `max_retries` ceiling and curfew check
- Don't remove `--allowedTools` write restrictions for unattended runs
- Don't store credentials in the Obsidian vault or git
- Don't inject more than ~2KB of memory context per query
- Don't use Opus for tasks Haiku or Gemini can handle adequately
- Don't include potentially private personal details in repo files — keep docs generic enough to be public

---

## Writing and Communication Style

**Voice.** Direct and precise — technically astute professional, not a customer
service bot. Take clear positions. Hedge only when genuine uncertainty exists.
Never open with: "Certainly", "Absolutely", "Great question", "Of course", "Sure".

**Formatting.** Prose over bullets. No unnecessary headers. Minimise bold —
reserve for truly critical terms. No closing summaries unless requested.

**Vocabulary to avoid.**
- Filler: genuinely, truly, honestly, straightforward, it's worth noting
- Clichés: delve, tapestry, nuanced, multifaceted, holistic, robust, pivotal, leverage, ecosystem
- Openers: "In today's world", "Let's dive in", "In conclusion", "To summarise"

**Tone.** Match register to context. Casual questions get casual answers.

**Australian English.** organise, colour, recognise, catalogue, behaviour.
Exception: "program" not "programme" for software contexts.

---

## Current Development State

- **Stage:** Spike 1 — Telegram channel integration
- **No agent engine code exists yet** — orchestrator (`claude_orchestrator.py`) is operational
- Spike goal: send a Telegram message, receive a Claude response

| Phase | Status |
|---|---|
| 0: Batch orchestrator | Done ✅ |
| 1: Telegram channel | Active |
| 2: Persistent memory | Pending |
| 3: Google services via MCP | Pending |
| 4: LlamaIndex RAG | Pending |
| 5: Proactive behaviours | Pending |

---

## Revision History

| Date | Version | Changes | Author |
|---|---|---|---|
| 2026-02-18 | 0.1 | Initial CLAUDE.md | Claude |
| 2026-03-08 | 0.2 | Restructured: added invariants/BR table, DO/DON'T, LLM routing table, current dev state; aligned with MusicElo CLAUDE.md structure | Claude |
