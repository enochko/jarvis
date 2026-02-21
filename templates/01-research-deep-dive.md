
# Research Deep Dive

## Prompt Template

```
Read my notes in [PATH_TO_NOTES].

Research this topic thoroughly. Use web search to find current information,
authoritative sources, and contrasting viewpoints.

Write a comprehensive report to [PATH_TO_OUTPUT] with:
- Executive summary (3-5 sentences)
- Key findings organized by theme
- Evidence and source citations
- Contrasting viewpoints or open debates
- Gaps in available information
- Recommended next steps or areas for further investigation

Target length: [SHORT ~1000 words | MEDIUM ~2500 words | LONG ~5000 words]
Audience: [technical peer | non-technical stakeholder | personal reference]
```

## Example

```
Read my notes in ~/research/fabric-vs-databricks-notes.md.

Research the current state of Microsoft Fabric vs Databricks for
mid-size enterprise data platforms. Use web search for the latest
pricing, feature comparisons, and community sentiment.

Write a report to ~/research/fabric-vs-databricks-report.md with:
- Executive summary
- Feature comparison by category (ETL, governance, cost, ecosystem)
- Strengths and weaknesses of each
- Recommendation for a 200-person consulting firm context
- Sources cited

Target length: ~2500 words
Audience: IT leadership making a platform decision
```

## Tips

- The more specific your notes, the more targeted the research
- Include what you already know so Claude doesn't repeat it
- Specify the decision you're trying to make if applicable
- Ask for a specific structure if you have one in mind
