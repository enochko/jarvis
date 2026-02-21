# Document Drafting & Writing

## Prompt Template

```
Read my notes/outline in [PATH_TO_NOTES].

Write a [DOCUMENT TYPE] to [PATH_TO_OUTPUT].md.

Context:
- Purpose: [what this document needs to achieve]
- Audience: [who will read it]
- Tone: [formal/professional/casual/technical]
- Length: [target word count or page count]

Structure: [specify sections or let Claude propose one]

Constraints:
- [e.g., must include specific data points from notes]
- [e.g., avoid jargon, executive audience]
- [e.g., follow company template style]
```

## Example: Technical Proposal

```
Read my rough notes in ~/docs/data-governance-notes.md.

Write a proposal document to ~/docs/data-governance-proposal.md.

Context:
- Purpose: Propose a data governance framework for [Company] ITSM reporting
- Audience: Senior Director of IT
- Tone: Professional, concise, recommendation-focused
- Length: ~1500 words

Structure:
1. Executive Summary
2. Current State / Problem Statement
3. Proposed Framework
4. Implementation Approach (phased)
5. Resource Requirements
6. Expected Outcomes
7. Risks and Mitigations

Constraints:
- Reference specific pain points from my notes
- Include a simple maturity model (levels 1-4)
- Keep recommendations actionable, not theoretical
```

## Example: Email Draft

```
Read the context in ~/docs/ivanti-uat-status.md.

Draft an email to ~/docs/ivanti-uat-email.md.

Context:
- Purpose: Update stakeholders on Ivanti Finance Service Request UAT status
- Audience: Project sponsor and business stakeholders
- Tone: Professional, clear on blockers without blame

Include: current status, what's complete, blockers, next steps, timeline impact.
Keep under 300 words.
```

## Tips

- Provide your rough notes — even bullet points give Claude much better context
- Specify word count to prevent over-writing
- "Recommendation-focused" vs "analysis-focused" changes the output significantly
- For iterative drafting: ask Claude to write v1, then review and refine in follow-up prompts
