# Data Analysis & Report Generation

## Prompt Template

```
Read the data in [PATH_TO_DATA].
[If applicable: the data dictionary/schema is at PATH_TO_SCHEMA.]

Analyze this data and produce a report at [PATH_TO_REPORT].md.

Analysis goals:
- [Specific questions to answer]
- [Metrics to calculate]
- [Comparisons to make]

Include:
- Summary statistics and key findings
- Visualizations saved as images in [PATH_TO_IMAGES_DIR]
  (embed in the markdown report)
- Data quality issues encountered
- Methodology notes (what you did and why)
- Caveats and limitations

Tools: Python (pandas, matplotlib/seaborn, scipy as needed)
```

## Example: ITSM Incident Analysis

```
Read the incident export in ~/data/itsm/incidents-jan-feb-2026.csv.

Analyze for the monthly IT Service Delivery report:
- Incident volume trends (daily, weekly)
- MTTR (mean time to resolve) by priority and category
- SLA compliance rates
- Top 10 recurring incident categories
- Comparison to previous period if prior data exists in ~/data/itsm/

Produce:
- Report: ~/reports/itsm-incident-analysis-feb2026.md
- Charts: ~/reports/charts/ (PNG, embedded in report)
- Summary table suitable for pasting into a PowerPoint

Use seaborn for charts with a clean, professional style.
```

## Example: Quick EDA

```
Read ~/data/dataset.csv and give me a quick exploratory analysis.

Save to ~/reports/eda-report.md:
- Shape, dtypes, missing values
- Distributions of numeric columns
- Correlations
- Obvious outliers or data quality issues
- 3-5 observations worth investigating further

Keep it concise — this is a first look, not a deep dive.
```

## Tips

- Specify the output format explicitly (markdown, CSV summary, charts)
- For large datasets, tell Claude to sample or summarize rather than process everything
- Ask for "methodology notes" so you can verify the approach
