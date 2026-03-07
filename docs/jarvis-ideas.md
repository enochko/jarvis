---
date created: 2026-03-08
date modified: 2026-03-08
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

---

## Tier 1 — High value, lower effort (do these after core spikes)

### 1. Periodic notes auto-assembly (MBP / Mac mini)
**What**: Agent runs at 9PM, reads calendar events, git commits, completed Obsidian tasks, and Telegram conversation log for the day, then assembles a draft daily note. You edit the interpretation; the agent handles the mechanical assembly. Weeklies drafted from dailies on Sunday. Monthlies from weeklies.

**Why it matters**: Daily notes fail because the friction of writing exceeds perceived value. This eliminates the friction. 5 minutes editing vs 30 minutes writing from scratch.

**Dependencies**: Phase 1 (Telegram) + Phase 2 (memory/logging) + Google Calendar MCP.

**Overnight risk**: Low. Read-only except for writing the draft note. Idempotent — rerunning overwrites the same file.

---

### 2. Finance data-intake automation (Mac mini, sensitive data local-only)
**What**: Agent ingests bank/investment transaction exports (CSV), updates the financial snapshot in Obsidian, flags when configured portfolio transitions are complete, and generates a quarterly spending summary.

**Why it matters**: You currently do this manually and quarterly. High-value recurring task that's entirely mechanical except for the summary narrative.

**Dependencies**: Phase 4B (LlamaIndex over Finance folder) for historical queries. Basic version (CSV parsing → Obsidian update) works with just Phase 1.

**Overnight risk**: Medium. Write operations to Finance folder. Ensure `.claudeignore` excludes Finance from cloud LLM access; only Ollama/local processing.

---

### 3. Movie/TV auto-organiser (Mac mini)
**What**: Agent monitors a pending/staging folder on the Mac mini, matches filenames to TMDB/TVDB via API, renames consistently (space-separated, no decimals), moves to the correct `Movies/` or `TV Shows/Season X/` structure. Deduplicates: keep max resolution, 1 SDR + 1 HDR max.

**Why it matters**: You drop files in a staging folder today and manually organise them. This is entirely automatable — filename parsing + API lookup, no vision model needed.

**Dependencies**: Mac mini as always-on host. Python + TMDB API key (free). No LLM strictly required for most cases; Sonnet useful for ambiguous filenames.

**Overnight risk**: Low. Write operations confined to media drives. Dry-run mode first.

---

### 4. MDS study support — private tutor mode (MBP)
**What**: Local model (or Claude Code) with course materials as context — lecture PDFs, your Obsidian notes for the subject, past assignments. Serves as a private Q&A partner between study sessions. Particularly useful for active semester subjects.

**Why it matters**: No data leaves the house for your own academic work. Useful in low-effort maintenance mode during busy weeks.

**Dependencies**: Phase 4 (LlamaIndex over vault + uni materials). Interim version works with Claude Code + manual file references right now.

**Overnight risk**: None. Interactive use only.

---

## Tier 2 — High value, higher effort or hardware dependency

### 5. Photo/video organisation pipeline (Mac mini, vision model required for classification)
**What**: Multi-stage pipeline:
1. **Metadata pass** (no LLM): ExifTool extracts taken date → move to `YYYY/YYYY-MM/` structure. Pure metadata, fast.
2. **Heuristic pass**: Screenshots detected by dimensions/source metadata. Social media/memes by source app metadata. Most content sorted without a model.
3. **Vision classification pass** (Ollama + vision model): Remaining unclassified content flagged by category. Sensitive content → review folder, not auto-sorted. Low-confidence → human review queue.

**Why staged**: Most of the work (90%+) is metadata operations. Vision model only needed for the genuinely ambiguous slice. This makes the pipeline fast and cheap even before the Mac mini arrives.

**Dependencies**: Mac mini M5 Pro 64GB for vision classification at useful quality (Qwen2.5-VL 32B+). Metadata pass works on MBP today.

**Video**: Extract keyframes via ffmpeg, classify frames. More complex — build photo pipeline first.

**Overnight risk**: Medium-high. Destructive file moves. Build dry-run mode first; verify output structure before enabling writes. Never delete originals until a second pass confirms.

---

### 6. Book deduplication and library cataloguing (MBP / Mac mini)
**What**: Scan book collection across all folders (personal development, productivity, data science, programming, etc.). Hash-based deduplication (same file, different folders). Consistent naming. LLM pass to suggest better categorisation where a book spans multiple categories. Generate reading list index in Obsidian.

**Why it matters**: Currently the same book might exist in 3 folders. Finding "do I have X?" requires manual searching.

**Dependencies**: Phase 1 + basic scripting. Ollama for the categorisation suggestion pass (doesn't need frontier model).

**Overnight risk**: Low. Read-only cataloguing first, then write operations only to rename/move on explicit confirmation.

---

### 7. Remote access via Tailscale + iOS Shortcuts (MBP + Mac mini)
**What**: Tailscale mesh across all devices (MBP, Mac mini, iPhone, iPad). Jarvis API running on Mac mini reachable from anywhere. iOS Shortcuts calling the local API: "Research this tonight", "Add to Obsidian inbox", "What's on my calendar?".

**Why it matters**: Jarvis becomes accessible from your phone regardless of where you are. The Mac mini is the always-on agent host; MBP and iOS are thin clients.

**Dependencies**: Phase 1 (FastAPI service running on Mac mini). Tailscale setup is a one-time 30-minute task.

**Overnight risk**: None. Auth via Tailscale ACLs + ALLOWED_USERS whitelist.

---

### 8. Korean language practice agent (MBP / Mac mini)
**What**: Local model or Claude Code as low-stakes conversation partner between tutoring sessions. Vocabulary drilling, reading practice, Anki card generation from new words encountered. Spaced repetition prompts via Telegram.

**Why it matters**: Useful in maintenance mode when you don't have a session scheduled. Fills the gap between formal lessons.

**Dependencies**: Phase 1 (Telegram channel). Anki card generation already in prompt templates. Conversation partner mode needs Phase 1 + a decent local model.

**Overnight risk**: None. Read/write to `~/korean/` only.

---

## Tier 3 — Nice to have, lower priority given time constraints

### 9. Paperless/document archive RAG (Mac mini, local-only)
**What**: LlamaIndex over the full document archive (receipts, warranties, transcripts, etc.). Natural language queries: "What warranty do I have for the dishwasher?", "When was my last car service?".

**Dependencies**: Phase 4 infrastructure + Mac mini for the 47GB initial indexing pass. Initial text extraction from PDFs is an overnight batch job.

**Privacy note**: Entirely local pipeline — Ollama embeddings, FAISS, Ollama LLM for queries. No document content leaves the house.

---

### 10. Receipt parsing → daily notes enrichment (Mac mini)
**What**: Parse receipts from Paperless locally (OCR → date, vendor, amount). Inject spending summary lines into auto-generated daily notes. "Spent $85 at Coles, $42 at Shell."

**Dependencies**: Idea 9 (document archive indexing) + Idea 1 (periodic notes). Build those first.

---

### 11. Plex/Jellyfin + Jarvis recommendation layer (Mac mini)
**What**: Install Plex or Jellyfin first (standard solution for media browsing). Jarvis layer on top for natural language queries ("what should we watch tonight?"), mood-based recommendations from your actual library, and search across your collection.

**Recommendation**: Plex or Jellyfin first, standalone. The browsing/organisation problem is solved. Only build the Jarvis layer if natural language search becomes a genuine need.

**Dependencies**: Idea 3 (movie/TV organiser) should run first to clean up the library structure.

---

### 12. MBP ↔ Mac mini job passing (Mac mini)
**What**: SSH or lightweight FastAPI for submitting jobs from MBP to Mac mini. Lets you trigger a Mac mini agent task from the MBP without being physically at the machine. Pairs with Tailscale (Idea 7) for full remote access.

**Dependencies**: Phase 1 FastAPI service. Straightforward once the service exists.

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

---

## Suggested sequencing given time constraints

1. **Finish Spike 1** (Telegram ↔ Claude) — everything else depends on this.
2. **Spike 2** (memory/logging) — needed for periodic notes and Korean agent.
3. **Periodic notes** (Idea 1) — highest recurring ROI, unlocks after Spike 2 + Calendar MCP.
4. **Movie/TV organiser** (Idea 3) — self-contained, Mac mini task, clear win once hardware arrives.
5. **Study support** (Idea 4) — semester-aligned, useful now with basic Claude Code + file references.
6. **Photo metadata pipeline** (Idea 5, metadata pass only) — start this before Mac mini; vision pass deferred.
7. **Everything else** — after Mac mini arrives and core spikes are stable.
