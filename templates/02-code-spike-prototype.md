# Code Spike / Prototype

## Prompt Template

```
Read the requirements in [PATH_TO_NOTES].

Build a working spike/prototype that demonstrates [WHAT].

Requirements:
- Language/framework: [e.g., Python, Java, React]
- Key functionality to prove out: [list specifics]
- Output location: [PATH_TO_OUTPUT_DIR]
- Include a README.md explaining how to run it

Constraints:
- [e.g., must work offline, no paid APIs, specific library versions]
- [e.g., performance target, data volume to handle]

Write tests that verify the core functionality works.
```

## Example: Ranking Algorithm Spike

```
Read the requirements in ~/projects/my-project/prd.md.

Build a spike that demonstrates the Glicko-2 ranking algorithm
working with sample data.

Requirements:
- Language: Python
- Prove out: Glicko-2 rating updates after head-to-head comparisons,
  rating convergence over multiple rounds, rating deviation decay
- Output: ~/projects/my-project/spikes/glicko2-spike/
- Include README.md with setup and run instructions

Constraints:
- Use glicko2 PyPI package or implement from scratch (compare both)
- Seed with 50 sample items from a CSV
- Simulate 200 comparisons and show rating distribution

Write pytest tests that verify:
- Ratings move in expected direction after a comparison
- Rating deviation decreases with more comparisons
- New songs have high uncertainty, frequently-compared songs converge
```

## Tips

- Spikes are throwaway — tell Claude to optimize for speed of learning, not production quality
- Ask it to document what it learned and decision points for the real implementation
- Request a "spike findings" summary at the end
