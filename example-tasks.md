---
default_model: sonnet
default_output_dir: ~/Obsidian/aaa-claude/claude-outbox
curfew: "11:00"
retry: 4
write_dirs:
  - ~/Obsidian/aaa-claude/claude-outbox
  - ~/Obsidian/aaa-claude/claude-inbox
  - ~/korean
  - ~/projects/musicelo/spikes
  - ~/uni
  - ~/claude-output
---

# Tonight's Tasks

## Simple flat checklist format (good for quick tasks)

- [ ] Testing if Claude Code works. Respond with a YES file.
- [ ] Read [[Korean Lesson 2026-02-17]] and generate Anki cards as TSV to ~/korean/anki-import.tsv {model: haiku}
- [ ] Summarise the key points from [[MusicElo v3 PRD]] into a one-pager {model: sonnet, output: ~/Obsidian/aaa-claude/claude-outbox/musicelo-summary.md}

## Detailed sectioned format (good for complex tasks)

## Task: Research Microsoft Fabric Governance
- model: opus
- schedule: 01:00
- output: ~/Obsidian/aaa-claude/claude-outbox/fabric-governance-report.md
- retry: 4

Read my notes in [[Fabric Governance Notes]].

Research current best practices for data governance in Microsoft Fabric,
specifically for mid-size consulting firms.

Write a comprehensive report covering:
- Executive summary
- Data governance framework options within Fabric
- OneLake security model and workspace permissions
- Comparison with Purview integration
- Recommended phased implementation approach
- Sources cited

Target length: ~2500 words
Audience: Senior IT Director

## Task: Review Assignment Draft
- model: opus
- schedule: 02:00
- output: ~/Obsidian/aaa-claude/claude-outbox/assignment-review.md

Review my assignment at [[Assignment Draft]] against the spec
at [[Assignment Spec]].

Course: [Course Name]
Check for:
- Correct methodology and approach
- Proper use of relevant techniques
- Interpretation and reasoning quality
- Code correctness (if applicable)
- Alignment with marking criteria

Write review with issues ranked by severity.
Do NOT rewrite my work -- flag issues for me to fix.
