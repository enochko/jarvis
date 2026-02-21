# Anki Card Review & Generation

## Review Existing Cards

```
Read my Anki cards exported at [PATH_TO_EXPORT].
[If applicable: the source material is at PATH_TO_SOURCE.]

Review the cards for:
- Adherence to Fluent Forever / minimum information principle
  (one atomic fact per card, no sets/enumerations unless mnemoniced)
- Cloze deletions that are too vague or have multiple valid answers
- Cards that test recognition instead of recall
- Redundant or near-duplicate cards
- Missing cards for key concepts in the source material

Write a review to [PATH_TO_REVIEW].md listing:
- Cards to fix (with suggested rewording)
- Cards to delete (with reason)
- New cards to add (with full card text)
```

## Generate New Cards from Source Material

```
Read the source material in [PATH_TO_SOURCE].
[If applicable: my existing cards are at PATH_TO_EXISTING.]

Generate Anki cards following these principles:
- Fluent Forever methodology
- One atomic fact per card
- Use cloze deletions where appropriate
- Front should be a specific, unambiguous prompt
- Back should be concise (ideally <15 words)
- Include context/hint on front if needed to disambiguate
- For formulas: test both recognition and application
- For definitions: test in both directions where useful

Output format: [TSV for import | Markdown table | .apkg if possible]
Write to: [PATH_TO_OUTPUT]

Do NOT generate cards for trivial facts or things I'd already know
from prerequisites.
```

## Example: Language Vocabulary Cards

```
Read my language lesson notes from ~/study/lesson-notes-2026-02-15.md.

Generate Anki cards following Fluent Forever principles:
- Vocabulary cards: target language → image/context description (no L1 on front)
- Grammar cards: pattern cloze with natural example sentences
- Pronunciation cards only for non-obvious patterns
- Tag each card with the lesson date and topic

Skip words I likely already know (check against
~/study/existing-vocab-export.txt if available).

Output as TSV (front, back, tags) to ~/study/anki-import-2026-02-15.tsv.
```

## Example: University Course Cards

```
Read the lecture slides in ~/uni/stats-course/week3-slides.pdf
and my lecture notes in ~/uni/stats-course/week3-notes.md.
Existing cards: ~/uni/stats-course/anki-export.txt

Generate Anki cards for [Course Name] Week 3.

Focus on:
- Key theorems and their conditions/assumptions
- When to use each model/test (decision-making cards)
- Common pitfalls and their solutions
- Formula cards that test *application* not just recall
- Interpretation cards (e.g., "what does it mean when...")

Skip anything already covered in existing cards.
Output as TSV to ~/uni/stats-course/anki-import-week3.tsv.
```

## Tips

- Export existing cards first so Claude can avoid duplicates
- For language cards, specify your L1/L2 direction preference
- For technical cards, "application over recall" produces better retention
- TSV is easiest to import into Anki (File → Import)
