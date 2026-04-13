# Project Jarvis: Personal AI Assistant

**Codename: Jarvis  
**Status:** Scoping → Spike 1  
**Date:** 2026-02-18  
**Author:** [Your Name]  

---

## Vision

A personal AI assistant running on your Mac, accessible through multiple
channels (Telegram, web UI, Apple Watch voice, CLI), backed by multi-provider
LLM execution (Claude, Gemini, Codex, Ollama), your Obsidian vault for
persistent memory and knowledge, and integrations for Gmail, Google Calendar,
Google Drive, and local document search via LlamaIndex RAG.

Telegram is the first channel. The agent engine is the product.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│               CHANNELS                       │
│                                              │
│  Telegram  │  Web UI  │  Watch  │  CLI       │
│  (mobile)  │ (desktop)│ (voice) │ (terminal) │
└─────┬──────┴────┬─────┴────┬────┴───┬───────┘
      │           │          │        │
      ▼           ▼          ▼        ▼
┌─────────────────────────────────────────────┐
│         GATEWAY / API LAYER                  │
│  (FastAPI on localhost:8000)                 │
│  - Auth per channel                          │
│  - Message normalisation (text/voice→text)   │
│  - Response formatting per channel           │
│  - Session management                        │
│  - Bot commands (/usage, /remember, /task)   │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌──────────────┐  ┌───────────────────────┐
│  LLM Router  │  │  LlamaIndex RAG       │
│              │  │  (context retrieval)   │
│  claude -p   │  │                       │
│  codex -p    │  │  Ollama embeddings    │
│  gemini -p   │  │  FAISS vector store   │
│  ollama API  │  │  Distill dedup (opt.) │
└──────┬───────┘  └───────────┬───────────┘
       │                      │
       ▼                      ▼
┌─────────────────────────────────────────────┐
│  DATA LAYER                                  │
│                                              │
│  Obsidian Vault (~/Obsidian)                 │
│  - Memory: jarvis-memory/ (facts + logs)       │
│  - Knowledge: all notes (indexed by RAG)     │
│  - Tasks: claude-inbox/ + claude-outbox/     │
│  - Logs: jarvis-logs/                          │
│  - Security: .claudeignore exclusions        │
│                                              │
│  Google Services (via MCP)                   │
│  - Gmail, Calendar, Drive                    │
│                                              │
│  Batch Orchestrator                          │
│  - claude_orchestrator.py (overnight tasks)  │
└─────────────────────────────────────────────┘
```

**Key architectural decision:** The agent engine is a **separate local API
service**, not embedded inside any channel. Channels are thin clients.
This means adding a web UI or Watch app later just requires a new client
calling the same `localhost:8000` endpoint.

---

## LLM Provider Strategy

All three major providers now have CLI agents with headless mode:

| CLI | Provider | Model | Cost | Headless | Install |
|-----|----------|-------|------|----------|---------|
| `claude` | Anthropic | Opus/Sonnet/Haiku | Subscription | `claude -p` | `npm install -g @anthropic-ai/claude-code` |
| `codex` | OpenAI | GPT-5.3-Codex | Subscription or API | `codex -p` | `npm install -g @openai/codex` |
| `gemini` | Google | Gemini 2.5 Pro / 3 | **Free** (personal Google) | Headless supported | `npm install -g @google/gemini-cli` |
| `ollama` | Local | Qwen3, nomic-embed-text | **Free** (runs on Mac) | REST API | `brew install --cask ollama` |

Router logic:
```python
def select_provider(task):
    if task.provider:          # Explicit override
        return task.provider
    if is_coding_task(task):   # Code tasks → Claude (strongest)
        return "claude"
    if is_research(task):      # Research → Gemini (free, 1M context)
        return "gemini"
    if is_simple(task):        # Simple → Ollama (local, free) — only if quota exhausted
        return "ollama"
    return "claude"            # Default
```

Provider selection by use case:

| Use Case | Best Provider | Why |
|----------|--------------|-----|
| Complex reasoning, architecture | Claude (Opus) | Strongest at nuanced analysis |
| General coding, code review | Claude (Sonnet) or Codex | Both strong |
| Web research, summarisation | Gemini | Free, 1M token context |
| Bulk simple tasks (Anki cards) | Claude (Haiku) or Gemini | Cheap/free |
| Local doc search (embeddings) | Ollama (nomic-embed-text) | Free, private |
| Fallback when quota exhausted | Gemini (preferred) or Ollama | Gemini is faster/better; Ollama only if offline needed |
| Korean language tasks | Claude (Sonnet) | Best multilingual quality |
| Stats/math concepts | Claude or Gemini | Both strong |
| General coding tasks | Codex or Claude | Both strong at code |

---

## Phases

### Phase 0: Foundation & Batch Orchestrator (Done ✅)

**Delivered:**
- Python orchestrator (`claude_orchestrator.py`) for headless batch tasks
- Obsidian-compatible task files with YAML frontmatter
- Per-task model selection, scheduled start times, quota retry logic
- Curfew window (stops retries before morning to preserve daytime quota)
- Wikilink resolution for Obsidian `[[references]]`
- Write directory restrictions via `--allowedTools`
- Checkbox status updates and completion summaries
- 6 prompt templates (research, code spike, Anki cards, file dedup,
  data analysis, document drafting)
- Comprehensive guide (`CLAUDE-CODE-GUIDE.md`)

### Phase 1: First Channel — Telegram ↔ Agent Engine (MVP)

**Goal:** Text Claude from your phone, get responses back.  
**Effort:** 1-2 weekends  
**Dependencies:** Telegram account, Claude Code installed, Python 3.11+

| Component | Detail |
|-----------|--------|
| Agent engine | FastAPI service on `localhost:8000` |
| Telegram bot | `python-telegram-bot` → calls agent engine API |
| Auth | Whitelist your Telegram user ID (single user) |
| Execution | `claude -p "prompt" --model sonnet` via subprocess |
| Write protection | `--allowedTools` restricting writes to safe dirs |
| Response | Stdout captured, chunked if >4096 chars |
| Daemon | `launchd` plist on macOS (auto-start on boot) |
| Logging | All conversations to `~/Obsidian/aaa-claude/jarvis-logs/` |
| `/usage` command | Query Claude quota via undocumented OAuth API or ccusage |

**Starting point:** Fork `seedprod/claude-code-telegram` (MIT licensed).
Includes session persistence, launchd plist, voice transcription, daily
briefing skill. Modify to separate agent engine from Telegram layer.

Other references:
- `hanxiao/claudecode-telegram` — tmux + hooks approach, simpler
- `RichardAtCT/claude-code-telegram` — full SDK with rate limiting

**Key decision — CLI vs SDK:**
- CLI (`claude -p`): uses subscription quota, no API key, full tooling → **Recommended**
- SDK (`anthropic` Python package): needs API key (additional cost), more control

### Phase 2: Persistent Memory via Obsidian

**Goal:** Bot remembers context across sessions.  
**Effort:** 1 weekend  
**Dependencies:** Phase 1 working

| Component | Detail |
|-----------|--------|
| Hot cache | `jarvis-memory/hot.md` — compact end-of-session summary; read at next session start |
| Facts file | `jarvis-memory/facts.md` — persistent facts via `/remember` command; always injected as context |
| Context injection | Prepend `facts.md` + `hot.md` to each `claude -p` call (~1-2KB total) |
| `/remember` command | Appends to `facts.md` |
| Vault CLAUDE.md | Vault-root `CLAUDE.md` (separate from repo) instructs Claude Code to read/write hot cache on session start/end |
| mcp-obsidian | Evaluate as vault retrieval layer before committing to LlamaIndex for vault search (see Phase 4 note) |

**Revised from original plan:** Full conversation transcript logging is deprioritised
in favour of the hot cache pattern. The hot cache is more signal-dense — Claude writes
only what's worth carrying forward, not a full transcript. This is simpler to implement
and cheaper to inject as context.

**Token cost is small.** Context injection sends ~1-2KB (facts + hot cache summary),
not your whole vault. Full vault search is Phase 4, which retrieves only 5-10 relevant
chunks per query.

**Pre-Spike 2 quick win:** Create the vault-level `CLAUDE.md` and `hot.md` convention
now (before Spike 1 is complete) — it has zero dependencies and immediately improves
interactive Claude Code sessions. See `jarvis-ideas.md` Idea 13.

File structure:
```
~/Obsidian/aaa-claude/
├── CLAUDE.md                   # Vault-level context for Claude Code interactive sessions
├── jarvis-memory/
│   ├── facts.md                # Persistent facts (/remember commands)
│   ├── hot.md                  # Hot cache: compact summary updated each session
│   └── ...
├── claude-inbox/               # Batch tasks (orchestrator)
├── claude-outbox/              # Completed outputs
└── jarvis-logs/                # System logs
```

### Phase 3: Google Services via MCP

**Goal:** "What's on my calendar?" "Summarise my unread email."  
**Effort:** 2-3 weekends (OAuth setup is the hard part)  
**Dependencies:** Phase 1 working, Google Cloud project

| Service | MCP Server | Enables |
|---------|-----------|---------|
| Gmail | `google-gmail` MCP | "Any urgent emails?", email summaries |
| Calendar | `google-calendar` MCP | "Am I free Friday 3pm?", schedule queries |
| Drive | `google-drive` MCP | "Find the project governance doc" |

Setup:
1. Create Google Cloud project, enable Gmail/Calendar/Drive APIs
2. Create OAuth 2.0 credentials (desktop app type)
3. Run consent flow once for refresh token
4. Configure MCP servers in Claude Code

**Note:** MCP server registry changes rapidly. Check mcp.so and smithery.ai
for current Google integration options before starting.

**Security:** Scope OAuth tokens to read-only. Store credentials outside
vault (not in Obsidian, not in git).

### Phase 4: LlamaIndex RAG — Deep Knowledge Retrieval

**Goal:** "What did my notes say about X?" across your entire 108MB vault.  
**Effort:** 2-3 weekends  
**Dependencies:** Phase 2 working, Ollama installed

**Re-evaluate scope before starting:** The `mcp-obsidian` MCP server (set up during
Phase 2) may cover the vault Q&A use case without embeddings, using the Karpathy LLM
wiki pattern (well-structured markdown + hot cache, no vector DB). Assess its retrieval
quality on real queries before committing to LlamaIndex for the vault. LlamaIndex is
still the right tool for large non-vault collections (Paperless archive, 47GB PDFs)
where volume genuinely requires vector retrieval.

**Why not just send files to Claude?**
Your vault is 108.5MB / 1,643 files. Claude's context window can't hold it.
LlamaIndex creates vector embeddings of all docs, then per-query retrieves
only the 5-10 most relevant chunks (~2-5KB) to inject as context.

```python
# One-time: index vault (runs locally, free with Ollama embeddings)
docs = SimpleDirectoryReader("~/Obsidian", exclude=load_claudeignore()).load_data()
index = VectorStoreIndex.from_documents(docs)
index.storage_context.persist("~/jarvis-index/")

# Per-query: retrieve relevant context
retriever = index.as_retriever(similarity_top_k=5)
chunks = retriever.retrieve(user_question)
context = "\n".join([c.text for c in chunks])  # ~2-5KB

# Inject into Claude prompt
prompt = f"Context from my notes:\n{context}\n\nQuestion: {user_question}"
```

**Embedding model recommendation:**
- Start with Ollama + `nomic-embed-text` (free, local, good enough)
- Swap to OpenAI `text-embedding-3-small` if quality insufficient (~$1/month)
- FAISS as vector store (local, no server needed)

**Re-indexing:** Nightly cron rebuild, or incremental indexing on file change.

**Distill (context deduplication):**
Distill sits between LlamaIndex and Claude — deduplicates redundant
chunks before they reach the LLM. Relevant only once RAG is running
and you notice redundant context polluting responses. Not needed until
Phase 4 is mature. ~12ms overhead, no LLM calls, deterministic.

**Chat with colleague about their LlamaIndex setup — questions to ask:**
1. What hardware? (Mac? Linux server? GPU?)
2. Which embedding model? (OpenAI, Ollama/nomic, HuggingFace?)
3. Which vector store? (FAISS, Chroma, Qdrant?)
4. How do they handle re-indexing when docs change?
5. Query quality vs just using Claude directly?

### Phase 5: Proactive Behaviours

**Goal:** Jarvis does things without being asked.  
**Effort:** 1-2 weekends per behaviour  
**Dependencies:** Phases 1-3

| Behaviour | Implementation |
|-----------|---------------|
| Morning briefing | 7AM cron → summarise email + calendar → push to channel |
| Auto daily notes | 9PM cron → aggregate calendar, git, tasks → generate daily note |
| Weekly summary | Sunday cron → aggregate 7 daily notes → draft weekly review |
| Monthly/quarterly | Aggregate weeklies → draft review (you edit 5 min vs write 30 min) |
| Task reminders | Scan inbox for overdue → nudge via channel |
| Study reminders | Before lecture days → remind about prep |
| Korean vocab review | Daily prompt with spaced repetition stats |
| Weekly digest | Summarise what Jarvis did this week |

**On periodic notes:** The reason daily notes fail is the friction of
writing them exceeds the perceived value. An agent can auto-generate
dailies from signals (calendar, git commits, completed tasks, conversations),
draft weeklies from dailies, and monthlies from weeklies. You spend 5 minutes
editing instead of 30 minutes writing from scratch. This is one of the
highest-value applications of the whole project.

### Phase 6: Additional Channels (Future)

| Channel | Technology | Notes |
|---------|-----------|-------|
| Web UI (MBP/Mac Mini) | React/Next.js or simple HTML + FastAPI | Desktop interface |
| Apple Watch | WatchOS app + speech-to-text (Whisper via mlx-whisper or Apple Speech API) | Voice queries on walks |
| CLI | Direct `curl localhost:8000` or thin Python wrapper | Terminal power users |

All channels are thin clients calling the same agent engine API.
Telegram is Spike 1 because it's the fastest to stand up.

### Phase 7: Work Obsidian Vault Setup

**Goal:** Get Claude to help replicate personal vault config to work vault.  
**Effort:** 1 agent task (not a full phase)

Claude reads personal vault's `.obsidian/` config (plugins, templates, CSS
snippets, hotkeys) and generates a setup script or migration guide for the
work vault. Filter out personal-only plugins. Quick win task for the
batch orchestrator.

---

## Security

### .claudeignore

Created in vault root. Excludes sensitive files from all LLM access
(Claude Code reads, LlamaIndex indexing, Ollama processing).

```
# .claudeignore
**/Health-Medical/**
**/Finance/**
**/2FA/**
**/Passwords/**
**/Private/**
*.key
*.pem
```

The `.claudeignore` is a convention defined by Jarvis. Claude Code uses
`--allowedTools` for write restrictions, LlamaIndex uses exclude patterns
in `SimpleDirectoryReader`. The agent engine should read `.claudeignore`
and apply it consistently to all three systems.

### Items to Remove or Relocate before Giving LLM Access

| Category                        | Risk                   | Action                                         |
| ------------------------------- | ---------------------- | ---------------------------------------------- |
| 2FA backup codes (plaintext)    | Account compromise     | Move to password manager (1Password/Bitwarden) |
| API keys / tokens               | Service abuse          | Move to password manager                       |
| Passwords in plaintext          | Account compromise     | Move to password manager                       |
| Financial account numbers       | Identity theft         | .claudeignore or remove                        |
| Medical records                 | Privacy                | .claudeignore                                  |
| Work confidential docs          | Professional liability | Keep in work vault only                        |
| Private keys (SSH, GPG)         | System compromise      | Should never be in Obsidian                    |
| Other people's personal info    | Their privacy          | Audit and remove                               |

**Agent task to audit vault:**
```markdown
## Task: Audit Obsidian vault for sensitive content
- model: sonnet
Scan all files in ~/Obsidian for patterns indicating sensitive data:
- Backup code patterns (6-10 digit numbers in groups)
- API key patterns (sk-, ghp_, xoxb-, etc.)
- Password/secret/credential keywords near values
- SSH keys, PEM files
Output a report of files and line numbers to review.
Do NOT include the actual sensitive values in your report.
```

### Write Restrictions

The orchestrator builds `--allowedTools` flags:
- Read, Grep, Glob, LS: unrestricted (can read anything not in .claudeignore)
- Write, Edit: restricted to whitelisted directories only
- Bash: currently unrestricted (needed for scripts, pip, git)

### Credentials Storage

- Telegram bot token: env var, never in git or vault
- Google OAuth tokens: outside vault, outside git
- Ollama: no credentials (local only)

---

## Cost Analysis

| Component | Cost |
|-----------|------|
| Claude Code (via Pro/Max subscription) | $0 additional |
| Gemini CLI (personal Google account) | Free |
| Telegram Bot API | Free |
| Ollama (local LLM + embeddings) | Free |
| LlamaIndex (local FAISS + Ollama) | Free |
| Google Cloud (OAuth for Gmail/Calendar) | Free tier |
| OpenAI embeddings (if needed) | ~$1/month |
| **Total additional cost** | **$0 - $1/month** |

vs. hosted AI assistants: require separate API key or subscription, ~$20-100/month.

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Claude CLI quota limits | Tasks fail mid-run | Orchestrator retry logic, use Haiku/Gemini for simple tasks |
| Telegram bot token leaked | Someone controls bot | Env var, never commit, ALLOWED_USERS whitelist |
| Claude writes to wrong files | Data loss in vault | `--allowedTools` write restrictions + git backup |
| Google OAuth token compromise | Email/calendar exposed | Store outside vault, scope to read-only |
| Sensitive data sent to LLM | Privacy breach | .claudeignore, vault audit, remove 2FA/passwords |
| LlamaIndex re-indexing slow | Stale search results | Incremental indexing or nightly cron |
| `claude -p` interface changes | Bot breaks | Pin version, test after updates |
| Prompt injection via Telegram | Malicious commands | Single-user auth, input sanitisation |
| `+` in folder names breaks globs | .claudeignore fails | Test patterns, fall back to broader match |
| Undocumented /usage API changes | Quota monitoring breaks | Also use ccusage (reads local JSONL files) |

---

## Comparison: Jarvis vs Hosted AI Assistants

| Aspect | Jarvis | Hosted AI Assistant |
|--------|------|----------|
| Cost | $0 additional | $20-100/month API |
| Channels | Telegram first, web/watch later | Varies by product |
| LLM | Claude, Gemini, Codex, Ollama | Any (Claude, GPT, DeepSeek, local) |
| Execution | Claude Code (very strong) | Python scripts (varies) |
| Memory | Obsidian files (yours, portable) | Built-in (proprietary format) |
| Knowledge search | LlamaIndex RAG (you control) | Built-in skills |
| Setup effort | ~5 weekends across phases | 1-2 hours (but less control) |
| Security | You control everything | Varies; community plugins may carry risk |
| Maintenance | You maintain it | Depends on vendor/community |
| Learning value | Enormous (portfolio piece) | Low (install and use) |

---

## Development Process: Discovery Spikes

This project uses a lightweight "discovery spikes" process rather than
full PM ceremony. Each spike is a self-contained experiment with a
go/no-go decision.

**Per spike, document in Obsidian:**
- Goal (1 sentence)
- What we learned
- What worked / what didn't
- Decision: continue, pivot, or stop
- Time spent

**When to upgrade to full PM:**
- If this becomes a portfolio project with a write-up
- If you want to open-source it
- If someone else contributes

Your other projects warrant full PM rigor. Jarvis is exploratory infrastructure.

---

## Repo Contents (Phase 0)

| File | Description |
|------|-------------|
| `claude_orchestrator.py` | Batch task runner with Obsidian integration |
| `example-tasks.md` | Sample task file with YAML frontmatter |
| `claude-code-guide.md` | Comprehensive guide to Claude Code agent workflows |
| `templates/01-research-deep-dive.md` | Research report prompt template |
| `templates/02-code-spike-prototype.md` | Code spike/prototype template |
| `templates/03-anki-cards.md` | Anki card generation template |
| `templates/04-file-duplicates-organization.md` | File duplicate detection template |
| `templates/05-data-analysis-report.md` | Data analysis/reporting template |
| `templates/06-document-drafting.md` | Document drafting template |
| `README.md` | Project overview |

---

## Q&A Reference

### Conda vs Pip for Jarvis Packages

**Rule:** conda for Python itself and system-level dependencies; pip for all
application-specific packages.

```bash
conda activate jarvis
pip install python-telegram-bot fastapi llama-index ollama  # all pip
```

**Why:** `python-telegram-bot` and similar libraries move fast — PyPI has
current versions, conda-forge lags. More importantly, never run blind pip
upgrades (`pip install --upgrade $(pip list --outdated...)`) inside conda envs
— pip will take ownership of conda-managed packages and break conda's solver.

For the `jarvis` env specifically, update pip packages
deliberately one at a time, not via automated upgrade scripts.

**Conda env Python path for launchd/cron (no `conda activate`):**
```bash
conda run -n jarvis which python
# → /opt/homebrew/.../envs/jarvis/bin/python
# Use this absolute path in launchd plists and crontab
```

### Node.js: Brew Vs Conda Vs Docker?

**Install via brew. Don't conda it.**

Node.js is a system-level runtime, not a Python package. `brew install node`
is standard and what Claude Code/Gemini CLI/Codex all expect.

For Python isolation, use separate conda envs per project:
- `conda create -n jarvis python=3.11`
- Keep base conda clean

Docker: Learn it later when a project needs a database or Jarvis needs
proper daemon isolation. Don't let it block Phase 1.

### Other LLM CLIs

All three major providers have CLI agents. See LLM Provider Strategy
section above. Key insight: **Gemini CLI is free with a personal Google
account** — significant for bulk/research tasks.

### Local LLMs via Ollama

Ollama runs open-source LLMs entirely on your Mac. No internet, no API costs.

```bash
brew install --cask ollama     # Install (menu bar app)
ollama pull nomic-embed-text   # Embedding model for RAG (required)
# Chat models: only pull if you actually hit overnight quota problems
# Recommended if needed: qwen3:14b (~9GB, good multilingual/Korean support)
```

**Key insight from setup:** For interactive use, cloud models (Claude, Gemini) are
significantly faster and better quality than local models on M1 Pro. Don't pull
chat models speculatively — only add them if quota exhaustion becomes a real problem
during overnight batch runs.

Two uses for Jarvis:
1. **LlamaIndex embeddings** (Phase 4): `nomic-embed-text` for free local vector embeddings — this is the primary reason Ollama is in the stack
2. **Fallback LLM** (optional): `qwen3:14b` only if Claude/Gemini quota is consistently exhausted overnight. Prefer Gemini as fallback first (free, faster).

**Hardware context (M1 Pro, 32GB):** Can comfortably run up to 14B models at Q4
quantisation. Qwen3 recommended over Llama for Korean language support.

### Claude Code /usage Programmatically

No official `claude --usage` flag (heavily requested on GitHub). Workaround:

```bash
# OAuth token in macOS Keychain: "Claude Code-credentials"
# Undocumented API: GET https://api.anthropic.com/api/oauth/usage
# Headers: Authorization: Bearer <token>, anthropic-beta: oauth-2025-04-20
# Returns: { "five_hour": { "utilization": 0.37 }, "seven_day": { "utilization": 0.17 } }
```

Alternative: **ccusage** (`npx ccusage`) reads local JSONL log files. No API needed.

### Distill for Context Deduplication

Distill removes redundant chunks from RAG retrieval results before they
reach the LLM. Sits between LlamaIndex and Claude. Only relevant once
Phase 4 RAG is running and you notice redundancy. ~12ms overhead,
deterministic, no LLM calls. Not needed until Phase 4 is mature.

### Vault Size and Token Costs

Your vault (108.5MB, 1,643 files) is NOT sent to Claude in bulk:

```
108MB vault → LlamaIndex indexes ONCE (local, free with Ollama)
User question → retrieves 5-10 chunks (~2-5KB)
Those chunks + question → Claude (~3000 tokens, trivial)
```

Phase 2 memory injection is even smaller: ~1-2KB of facts + recent
conversation summaries.

### Colleague's LlamaIndex Setup

Likely running one of:
- **Full local:** Documents → LlamaIndex → Ollama embeddings → FAISS → Ollama LLM
- **Hybrid:** Documents → LlamaIndex → OpenAI embeddings → vector store → Claude/GPT

Ask them: hardware, embedding model, vector store, re-indexing strategy,
query quality vs direct Claude.

### Auto-generating Periodic Notes

Agent can auto-generate daily notes from signals (calendar, git, tasks,
conversations), draft weeklies from dailies, monthlies from weeklies.
You edit 5 minutes instead of write 30 minutes. Phase 5 feature, but
high-value motivation for the project.

### Work Obsidian Vault Setup

Quick agent task: Claude reads personal vault `.obsidian/` config, generates
migration guide for work vault. Filter personal-only plugins. Run as a
batch orchestrator task.

### Should This Have Full Product Management Process?

No. Discovery Spikes approach. See Development Process section above.
Upgrade to full PM if it becomes a portfolio project, goes open-source,
or gains contributors.

### Terms of Service Compliance

This section documents Jarvis's compliance with each LLM provider's Terms of
Service. Maintained as a good-faith record of due diligence.

#### Claude Code (Anthropic) — ✅ Compliant

**Relevant ToS clause (Consumer Terms, Section 3.7):**
> "Except when you are accessing our Services via an Anthropic API Key or
> **where we otherwise explicitly permit it**, to access the Services through
> automated or non-human means, whether through a bot, script, or otherwise."

**Why Jarvis is compliant:**

Claude Code (`claude -p`) is Anthropic's own officially released tool,
explicitly designed and documented for headless/non-interactive use via the
`-p`/`--print` flag. Using Claude Code in headless mode is the **explicitly
permitted** carve-out in the ToS clause above.

The January 2026 enforcement action that banned users targeted **third-party
harnesses** (Roo Code, Cline, OpenCode, etc.) that spoofed the Claude.ai web
interface via OAuth tokens — i.e., tools routing automation through the
consumer web product, not through Claude Code. Anthropic's own staff confirmed
this distinction: "we tightened our safeguards against spoofing the Claude Code
harness" (Thariq Shihipar, Anthropic MTS, January 2026).

**Jarvis architecture is explicitly on the sanctioned path:**
- Uses `claude -p` (Claude Code CLI) — Anthropic's tool, designed for this
- Single user only — no reselling or multi-user access
- Personal productivity use — not competing with or benchmarking Anthropic
- Respects quota limits — orchestrator retry logic backs off on quota errors
  rather than hammering the API
- No OAuth token exfiltration or third-party routing

**Data training note:** As of October 2025, Anthropic's Consumer Terms allow
model training on Claude Code sessions for Pro/Max users by default. You can
opt out in Settings → Privacy → Model Training. If you have sensitive vault
content routing through Claude Code, opt out.

---

#### Gemini CLI (Google) — ⚠️ Usable with caveats

**Authentication method matters:**

| Auth method | Data used for training? | Recommended for Jarvis? |
|-------------|------------------------|------------------------|
| Personal Google account (free) | **Yes** — prompts/responses collected for model training by default | External research tasks only |
| Google Workspace (paid) | No — treated as confidential | Yes, if available |
| API key (unpaid tier) | Yes | No |

**Jarvis usage guidance:**
- Use Gemini CLI for **external research tasks only** — web searches,
  summarisation of public content, tasks with no personal vault context
- **Do not** route Obsidian vault content, personal notes, medical/financial
  context, or any sensitive information through Gemini CLI on a personal account
- This aligns with the existing architecture: Gemini = external research,
  Claude = vault-aware tasks

**Usage statistics opt-out** (separate from training data):
```bash
# Opt out of usage telemetry
gemini /privacy  # or check ~/.gemini/config for telemetry settings
```

---

#### OpenAI Codex CLI — ⚠️ Requires existing ChatGPT subscription

**Availability:** Codex CLI is included with ChatGPT Plus, Pro, Business, and
Enterprise plans. It is **not free** — requires an active ChatGPT subscription
or API key (additional cost). Only viable for Jarvis if you already have a
ChatGPT subscription independent of Claude.

**ToS status:** Standard OpenAI consumer terms apply. No specific concerns for
personal automation use via the CLI, which is the sanctioned usage path
(equivalent to Claude Code's `claude -p`).

**Current recommendation:** Deprioritised. Claude Code covers coding tasks
better, Gemini CLI covers free research. Only add Codex if you have a ChatGPT
subscription already and want multi-provider redundancy.

---

## Action Items Checklist

### Immediate: Security & Setup (Before Spike 1)

- [x] Move 2FA backup codes from Obsidian plaintext to password manager
- [x] Audit vault for sensitive data (API keys, passwords, SSH keys, PII)
  - [x] Manually searched for: `sk-`, `ghp_`, `xoxb-`, `password`, `secret`, `credential`, `BEGIN RSA` — clean
- [x] Verify `.claudeignore` in vault root and patterns work
  - [x] Used simplified patterns without `+` prefix (e.g. `**/Health-Medical/**`, `**/Finance/**`) — confirmed folder names match
- [x] Install Node.js: `brew install node`
  - [x] Verify: `node --version` (18+)
- [x] Verify Claude Code: `claude --version`
  - [x] Test headless: `claude -p "say hello" --model sonnet`
- [x] Create conda env: `conda create -n jarvis python=3.11`
- [x] In jarvis env: `pip install python-telegram-bot pyyaml`
- [x] Test batch orchestrator with a real `tonight.md`

### Spike 1: Telegram ↔ Claude (1-2 weekends)

- [ ] Create Telegram bot via @BotFather → save token as env var
- [ ] Get Telegram user ID via @userinfobot
- [ ] Set env vars: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ALLOWED_USERS`
- [ ] Clone/fork `seedprod/claude-code-telegram`
- [ ] Get basic send → receive loop working
- [ ] Test from phone: send message, receive Claude response
- [ ] Set up `launchd` plist for auto-start on boot
- [ ] Add `/usage` command (ccusage or OAuth API)
- [ ] Write spike retrospective in Obsidian

### Spike 2: Memory + Obsidian (1 weekend)

- [ ] Create `~/Obsidian/aaa-claude/jarvis-memory/` directory
- [ ] Create `facts.md` for persistent facts
- [ ] Implement conversation logging (session → markdown)
- [ ] Implement context injection (facts + recent history → prompt prefix)
- [ ] Implement `/remember` command
- [ ] Test: does cross-session memory meaningfully improve responses?
- [ ] Write spike retrospective

### Spike 3: Google Services (2 weekends)

- [ ] Create Google Cloud project
- [ ] Enable Gmail, Calendar, Drive APIs
- [ ] Create OAuth 2.0 credentials (desktop app)
- [ ] Run consent flow, get refresh token
- [ ] Store credentials outside vault and git
- [ ] Check MCP server registry for current Google options
- [ ] Configure and test Gmail MCP
- [ ] Configure and test Calendar MCP
- [ ] Configure and test Drive MCP
- [ ] Test from Telegram: "What's on my calendar tomorrow?"
- [ ] Write spike retrospective

### Spike 4: LlamaIndex RAG (2-3 weekends)

- [ ] Talk to colleague about their LlamaIndex setup
- [ ] Ollama already installed; `nomic-embed-text` already pulled ✅
- [ ] In jarvis env: `pip install llama-index`
- [ ] Write indexing script with .claudeignore exclusions
- [ ] Index vault → persist to `~/jarvis-index/`
- [ ] Test retrieval quality on known questions
- [ ] Integrate into agent engine (retrieved context → prompt)
- [ ] Set up nightly re-indexing cron
- [ ] Evaluate if Distill dedup is needed
- [ ] Write spike retrospective

### Spike 5: Proactive Behaviours (ongoing)

- [ ] Auto daily notes (9PM cron: calendar + git + tasks → daily note)
- [ ] Morning briefing (7AM cron: email + calendar → Telegram)
- [ ] Weekly summary draft (Sunday cron: aggregate dailies)
- [ ] Korean vocab review prompt
- [ ] Study reminders before lecture days
- [ ] Write spike retrospective

### Optional / Future

- [ ] Install Gemini CLI: `npm install -g @google/gemini-cli` (free LLM)
- [ ] Install Codex CLI: `npm install -g @openai/codex` (if ChatGPT Plus)
- [ ] Add multi-provider support to orchestrator
- [ ] Refactor agent engine as proper FastAPI service
- [ ] Build web UI channel
- [ ] Explore Apple Watch voice channel (mlx-whisper)
- [ ] Work vault setup agent task
- [ ] Learn Docker for daemon isolation
- [ ] Write proper architecture doc after 4 spikes

---

## Ideas Backlog

Moved to `docs/jarvis-ideas.md`. That file covers prioritised ideas across file management,
automation, hardware (Mac mini M5 Pro), and future capabilities — with effort/value scoring
and a suggested sequencing given time constraints.
