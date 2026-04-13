---
date created: 2026-03-08
date modified: 2026-04-14
tags: [jarvis, ideas, backlog]
---

# Project Jarvis — Ideas Backlog & Prioritisation

This doc consolidates ideas raised across scoping sessions. Separate from the
formal phase roadmap in `scope.md`, which covers the committed spike sequence.

---

## Prioritisation Framework

Given time constraints (semester + work), ideas are scored on two axes:

- **Value**: How much recurring friction does this eliminate, or how much capability does it unlock?
- **Effort**: How much implementation work, ignoring hardware dependencies?

Hardware note: ideas marked **Mac mini** require the M5 Pro (64GB) to run properly.
Ideas marked **MBP** work on your current setup today.

### Jarvis vs Claude.ai Projects

Not every idea belongs in Jarvis. Claude.ai Projects is cheaper and simpler for
interactive Q&A with your own notes — it handles context management transparently
and costs nothing beyond the subscription you already pay.

**Build it in Jarvis if it requires any of:**
- Scheduled/proactive execution (fires without you asking)
- Filesystem writes (outputs land directly in Obsidian or elsewhere)
- Chained tasks (output of one feeds the next)
- Sensitive local data (Finance, Health — must never leave the machine)
- External integrations Claude.ai can't reach (TMDB API, local CSV exports, etc.)

**Use Claude.ai Projects instead if it's:**
- Interactive Q&A with your notes as context
- Iterative drafting or reasoning where conversation history matters
- A one-shot "generate this document" task — just download the file

Ideas below are annotated with **[Jarvis]** or **[Claude.ai]** accordingly.
Hybrid ideas that have both a Jarvis component (e.g. scheduled delivery) and a
Claude.ai component (e.g. interactive Q&A) are marked **[Both]**.

---

## Tier 1 — High value, lower effort (do these after core spikes)

### 1. Periodic notes auto-assembly (MBP / Mac mini) — [Jarvis]
**What**: Agent runs at 9PM, reads calendar events, git commits, completed Obsidian tasks, and Telegram conversation log for the day, then assembles a draft daily note. You edit the interpretation; the agent handles the mechanical assembly. Weeklies drafted from dailies on Sunday. Monthlies from weeklies.

**Why Jarvis**: Scheduled trigger, filesystem writes, Google Calendar integration. Can't be done from Claude.ai.

**Why it matters**: Daily notes fail because the friction of writing exceeds perceived value. This eliminates the friction. 5 minutes editing vs 30 minutes writing from scratch.

**Dependencies**: Phase 1 (Telegram) + Phase 2 (memory/logging) + Google Calendar MCP.

**Overnight risk**: Low. Read-only except for writing the draft note. Idempotent — rerunning overwrites the same file.

---

### 2. Finance data-intake automation (Mac mini, sensitive data local-only) — [Jarvis]
**What**: Agent ingests Vanguard/bank transaction exports (CSV), updates the financial snapshot in Obsidian, flags when Claudine's portfolio transition is complete and triggers the auto-invest configuration change, and generates a quarterly spending summary.

**Why Jarvis**: Sensitive data that must stay local (Ollama only). Scheduled execution. Direct filesystem access to CSV exports Claude.ai can't reach.

**Why it matters**: You currently do this manually and quarterly. High-value recurring task that's entirely mechanical except for the summary narrative.

**Dependencies**: Phase 4B (LlamaIndex over Finance folder) for historical queries. Basic version (CSV parsing → Obsidian update) works with just Phase 1.

**Overnight risk**: Medium. Write operations to Finance folder. Ensure `.claudeignore` excludes Finance from cloud LLM access; only Ollama/local processing.

---

### 3. Movie/TV auto-organiser (Mac mini) — [Jarvis]
**What**: Agent monitors a pending/staging folder on the Mac mini, matches filenames to TMDB/TVDB via API, renames consistently (space-separated, no decimals), moves to the correct `Movies/` or `TV Shows/Season X/` structure. Deduplicates: keep max resolution, 1 SDR + 1 HDR max.

**Why Jarvis**: Filesystem writes, external API calls, always-on monitoring. No interactive component.

**Why it matters**: You drop files in a staging folder today and manually organise them. This is entirely automatable — filename parsing + API lookup, no vision model needed.

**Dependencies**: Mac mini as always-on host. Python + TMDB API key (free). No LLM strictly required for most cases; Sonnet useful for ambiguous filenames.

**Overnight risk**: Low. Write operations confined to media drives. Dry-run mode first.

---

### 4. MDS study support — private tutor mode (MBP) — [Claude.ai until Phase 4, then Both]
**What**: Course materials as context — lecture PDFs, Obsidian notes for the subject, past assignments. Serves as a private Q&A partner between study sessions. Particularly useful for R (MAST90139) and Java (COMP90041) this semester.

**Why Claude.ai for now**: Interactive Q&A with files as context is exactly what Claude.ai Projects does well. Attach the relevant PDFs and notes directly — no Jarvis needed yet.

**Why Both eventually**: Once Phase 4 RAG is running, Jarvis can retrieve relevant chunks automatically without you manually attaching files each session. The interactive Q&A part stays in Claude.ai or Telegram; the retrieval layer is Jarvis.

**Why it matters**: No data leaves the house for your own academic work. Useful in low-effort maintenance mode during busy weeks.

**Dependencies**: Phase 4 (LlamaIndex over vault + uni materials) for the Jarvis component. Interim: use Claude.ai Projects with files attached.

**Overnight risk**: None. Interactive use only.

---

## Tier 2 — High value, higher effort or hardware dependency

### 5. Photo/video organisation pipeline (Mac mini, vision model required for classification) — [Jarvis]
**What**: Multi-stage pipeline:
1. **Metadata pass** (no LLM): ExifTool extracts taken date → move to `YYYY/YYYY-MM/` structure. Pure metadata, fast.
2. **Heuristic pass**: Screenshots detected by dimensions/source metadata. Social media/memes by source app metadata. Most content sorted without a model.
3. **Vision classification pass** (Ollama + vision model): Remaining unclassified content flagged by category. Sensitive content → review folder, not auto-sorted. Low-confidence → human review queue.

**Why Jarvis**: Scheduled batch, filesystem writes, local-only vision model. No interactive component.

**Why staged**: Most of the work (90%+) is metadata operations. Vision model only needed for the genuinely ambiguous slice. This makes the pipeline fast and cheap even before the Mac mini arrives.

**Dependencies**: Mac mini M5 Pro 64GB for vision classification at useful quality (Qwen2.5-VL 32B+). Metadata pass works on MBP today.

**Video**: Extract keyframes via ffmpeg, classify frames. More complex — build photo pipeline first.

**Overnight risk**: Medium-high. Destructive file moves. Build dry-run mode first; verify output structure before enabling writes. Never delete originals until a second pass confirms.

---

### 6. Book deduplication and library cataloguing (MBP / Mac mini) — [Jarvis]
**What**: Scan book collection across all folders (personal development, productivity, data science, programming, etc.). Hash-based deduplication (same file, different folders). Consistent naming. LLM pass to suggest better categorisation where a book spans multiple categories. Generate reading list index in Obsidian.

**Why Jarvis**: Filesystem operations, Obsidian index output. The cataloguing result lands in the vault automatically.

**Why it matters**: Currently the same book might exist in 3 folders. Finding "do I have X?" requires manual searching.

**Dependencies**: Phase 1 + basic scripting. Ollama for the categorisation suggestion pass (doesn't need frontier model).

**Overnight risk**: Low. Read-only cataloguing first, then write operations only to rename/move on explicit confirmation.

---

### 7. Remote access via Tailscale + iOS Shortcuts (MBP + Mac mini) — [Jarvis]
**What**: Tailscale mesh across all devices (MBP, Mac mini, iPhone, iPad). Jarvis API running on Mac mini reachable from anywhere. iOS Shortcuts calling the local API: "Research this tonight", "Add to Obsidian inbox", "What's on my calendar?".

**Why Jarvis**: Infrastructure that makes all other Jarvis ideas accessible remotely. Not a feature itself — a multiplier.

**Why it matters**: Jarvis becomes accessible from your phone regardless of where you are. The Mac mini is the always-on agent host; MBP and iOS are thin clients.

**Dependencies**: Phase 1 (FastAPI service running on Mac mini). Tailscale setup is a one-time 30-minute task.

**Overnight risk**: None. Auth via Tailscale ACLs + ALLOWED_USERS whitelist.

---

### 8. Korean language practice agent (MBP / Mac mini) — [Both]
**What**: Low-stakes conversation partner between AmazingTalker sessions. Vocabulary drilling, reading practice, Anki card generation from new words encountered. Spaced repetition prompts via Telegram.

**Why Both**: Anki card generation and spaced repetition prompts are Jarvis (scheduled, filesystem writes to `~/korean/`). The conversation partner component is better handled by Claude.ai or a local model — interactive back-and-forth where sending full history per turn through `claude -p` gets expensive fast.

**Why it matters**: Useful in maintenance mode when you don't have a session scheduled. Fills the gap between formal lessons.

**Dependencies**: Phase 1 (Telegram channel) for the Jarvis components. Conversation partner: Claude.ai Projects with lesson notes attached, or Ollama locally for cost-free practice.

**Overnight risk**: None. Read/write to `~/korean/` only.

---

## Tier 3 — Nice to have, lower priority given time constraints

### 9. Paperless/document archive RAG (Mac mini, local-only) — [Jarvis]
**What**: LlamaIndex over the full document archive (receipts, warranties, transcripts, etc.). Natural language queries: "What warranty do I have for the dishwasher?", "When was my last car service?".

**Why Jarvis**: Sensitive documents that must never leave the machine. Scheduled nightly re-indexing. Query interface via Telegram.

**Dependencies**: Phase 4 infrastructure + Mac mini for the 47GB initial indexing pass. Initial text extraction from PDFs is an overnight batch job.

**Privacy note**: Entirely local pipeline — Ollama embeddings, FAISS, Ollama LLM for queries. No document content leaves the house.

---

### 10. Receipt parsing → daily notes enrichment (Mac mini) — [Jarvis]
**What**: Parse receipts from Paperless locally (OCR → date, vendor, amount). Inject spending summary lines into auto-generated daily notes. "Spent $85 at Coles, $42 at Shell."

**Why Jarvis**: Local-only sensitive data, scheduled execution, Obsidian writes. Extension of idea 1.

**Dependencies**: Idea 9 (document archive indexing) + Idea 1 (periodic notes). Build those first.

---

### 11. Plex/Jellyfin + Jarvis recommendation layer (Mac mini) — [Both]
**What**: Install Plex or Jellyfin first (standard solution for media browsing). Jarvis layer on top for: "What should Claudine and I watch tonight?", mood-based recommendations from your actual library, natural language search ("that Korean thriller we downloaded last year").

**Why Both**: Plex/Jellyfin handles browsing (no Jarvis needed). The recommendation and natural language search layer is Jarvis — queries via Telegram against a local index of your library.

**Recommendation**: Plex or Jellyfin first, standalone. Only build the Jarvis layer if natural language search becomes a genuine need.

**Dependencies**: Idea 3 (movie/TV organiser) should run first to clean up the library structure.

---

### 12. MBP ↔ Mac mini job passing (Mac mini) — [Jarvis]
**What**: SSH or lightweight FastAPI for submitting jobs from MBP to Mac mini. Lets you trigger a Mac mini agent task from the MBP without being physically at the machine. Pairs with Tailscale (Idea 7) for full remote access.

**Why Jarvis**: Infrastructure extension of Phase 1 FastAPI service.

**Dependencies**: Phase 1 FastAPI service. Straightforward once the service exists.

---

### 13. Vault-level CLAUDE.md + hot cache (MBP) — [Jarvis]
**What**: A `CLAUDE.md` at the Obsidian vault root (separate from the repo `CLAUDE.md`) that instructs Claude Code how to navigate the vault during interactive sessions. Paired with a `jarvis-memory/hot.md` hot cache: at the end of each interactive Claude Code session, Claude writes a compact summary of what was discussed and changed; at the start of the next session, it reads that file first. Session continuity without full conversation logging.

**Why Jarvis**: Runtime convention for Claude Code interactive use. Not a Telegram feature — this governs the vault-as-second-brain workflow when you run `claude` in the terminal from inside `~/Obsidian/aaa-claude/`.

**Why it matters**: Eliminates context-rebuilding at the start of every session. You never have to re-explain where things are or what you were working on. The hot cache is simpler and more signal-dense than logging full conversation transcripts (Spike 2's original plan), because Claude writes only what's worth carrying forward.

**Relationship to Spike 2**: This partially replaces the conversation logging component of Spike 2. `facts.md` (persistent facts via `/remember`) stays as planned. Full session transcripts are deprioritised in favour of the hot cache pattern.

**Vault CLAUDE.md should cover**: vault folder structure and conventions, `.claudeignore` locations, `write_dirs` equivalent for interactive use, instruction to read `hot.md` on session start and update it on session end, pointer to `facts.md` for persistent facts.

**Overnight risk**: Low. Hot cache is a single small file, always overwritten. Idempotent.

**Dependencies**: None beyond Claude Code being installed. Implement before or during Spike 2.

---

### 14. mcp-obsidian vault server (MBP) — [Jarvis]
**What**: Install the `mcp-obsidian` MCP server (via Smithery or the Obsidian Local REST API plugin) to give Claude Code proper vault-aware access: full-text fuzzy search, backlink traversal, read/write with frontmatter support, works even when Obsidian is closed.

**Why Jarvis**: Replaces raw filesystem grep with vault-native search. Both Claude Code interactive sessions and Jarvis's Telegram agent benefit — the MCP server becomes the retrieval layer for vault queries.

**Why it matters**: Raw `grep` and `find` on the vault work but don't understand Obsidian structure (backlinks, tags, frontmatter queries). The MCP server does. This is materially better for the "what did I write about X?" use case. It also partially covers the Phase 4 LlamaIndex use case for the Obsidian vault specifically — LlamaIndex remains justified for the Paperless archive (47GB PDFs) but may be overkill for the vault itself.

**Relationship to Phase 4**: Evaluate `mcp-obsidian` search quality before committing to LlamaIndex for vault retrieval. The Karpathy LLM wiki pattern (structured markdown, no embeddings) may cover 80% of vault Q&A with far less infrastructure. LlamaIndex remains the right tool for Paperless and other large non-vault document collections.

**Setup**: Install Obsidian Local REST API plugin → configure MCP server in Claude Code's `~/.claude/mcp.json` → test with `claude mcp list`.

**Overnight risk**: None. Read-mostly; write operations still governed by `write_dirs`.

**Dependencies**: Spike 1 complete (so MCP config pattern is established). Can be done independently in parallel.

---

## Hardware considerations

| Idea | Works on MBP now | Needs Mac mini | Needs 64GB vision model |
|------|:-:|:-:|:-:|
| Periodic notes | ✓ | — | — |
| Finance automation | ✓ (careful) | Preferred | — |
| Movie/TV organiser | — | ✓ | — |
| Study support | ✓ | — | — |
| Photo/video classification | Metadata only | ✓ | ✓ |
| Book cataloguing | ✓ | — | — |
| Tailscale + iOS | — | ✓ | — |
| Korean agent | ✓ | — | — |
| Document archive RAG | — | ✓ | — |
| Receipt → daily notes | — | ✓ | — |
| Plex + Jarvis layer | — | ✓ | — |
| Vault CLAUDE.md + hot cache | ✓ | — | — |
| mcp-obsidian vault server | ✓ | — | — |

---

## Suggested sequencing given time constraints

1. **Finish Spike 1** (Telegram ↔ Claude) — everything else depends on this.
2. **Vault CLAUDE.md + hot cache** (Idea 13) — can be done now, zero dependencies, immediate benefit for interactive Claude Code use.
3. **Spike 2** (memory/logging) — hot cache replaces full conversation logging; focus on `facts.md` + `/remember` command + `mcp-obsidian` (Idea 14).
4. **Periodic notes** (Idea 1) — highest recurring ROI, unlocks after Spike 2 + Calendar MCP.
5. **Movie/TV organiser** (Idea 3) — self-contained, Mac mini task, clear win once hardware arrives.
6. **Study support** (Idea 4) — use Claude.ai Projects now; revisit after Phase 4 RAG.
7. **Photo metadata pipeline** (Idea 5, metadata pass only) — start this before Mac mini; vision pass deferred.
8. **Everything else** — after Mac mini arrives and core spikes are stable.
