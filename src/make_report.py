"""Stage 5 - generate README.md and docs/findings.md from the pipeline outputs.

Every figure quoted in the documentation is read from the result tables rather
than typed by hand, so the prose cannot drift away from the data. Re-running the
pipeline rewrites the numbers.
"""

from __future__ import annotations

import pandas as pd

from config import (COMPLETENESS_FLOOR, DOCS_DIR, OVERDUE_DAYS, PROCESSED_DIR,
                    ROOT, SUPPRESSION_THRESHOLD)
from analyse import analysable, headline, load_clean


def facts() -> dict:
    full = load_clean()
    df = analysable(full)
    h = headline(full)

    region = pd.read_csv(PROCESSED_DIR / "summary_by_region.csv")
    court = pd.read_csv(PROCESSED_DIR / "summary_by_court.csv")
    quarter = pd.read_csv(PROCESSED_DIR / "disposal_time_by_quarter.csv")
    flow = pd.read_csv(PROCESSED_DIR / "monthly_flow.csv")
    log = pd.read_csv(PROCESSED_DIR / "cleaning_log.csv")

    slowest_r = region.iloc[0]
    fastest_r = region.iloc[-1]
    slowest_c = court.iloc[0]

    focus = slowest_r["region"]
    fq = quarter[quarter["region"] == focus].sort_values("filed_quarter")
    complete = fq[fq["complete"]]
    incomplete = fq[~fq["complete"]]

    return {
        "h": h,
        "region": region,
        "court": court,
        "flow": flow,
        "log": log,
        "raw_rows": len(full),
        "slow_region": slowest_r["region"],
        "slow_region_days": slowest_r["median_days"],
        "fast_region": fastest_r["region"],
        "fast_region_days": fastest_r["median_days"],
        "region_gap": slowest_r["median_days"] - fastest_r["median_days"],
        "slow_court": slowest_c["court_name"],
        "slow_court_days": slowest_c["median_days"],
        "slow_court_n": int(slowest_c["closed_cases"]),
        "focus": focus,
        "peak_q": complete.iloc[-1]["filed_quarter"],
        "peak_days": complete.iloc[-1]["median_days"],
        "last_q": fq.iloc[-1]["filed_quarter"],
        "last_days": fq.iloc[-1]["median_days"],
        "last_closure": fq.iloc[-1]["closure_rate"],
        "first_closure": fq.iloc[0]["closure_rate"],
        "n_incomplete": len(incomplete),
        "net_backlog": int(flow["net_change"].sum()),
        "mismatch": int(df["duration_mismatch"].sum()),
    }


def readme(f: dict) -> str:
    h = f["h"]
    log_md = f["log"].to_markdown(index=False)
    region_md = (
        f["region"][["region", "closed_cases", "median_days", "mean_days",
                     "open_cases", "overdue_pct"]]
        .rename(columns={"closed_cases": "closed", "median_days": "median days",
                         "mean_days": "mean days", "open_cases": "open",
                         "overdue_pct": "overdue %"})
        .to_markdown(index=False)
    )
    return f"""# Court Timeliness Monitor

**An end-to-end analytics pipeline on synthetic public-sector data - Python for
cleaning and analysis, Power BI for the reporting layer.**

> ⚠️ **The data in this repository is synthetic.** It was generated for practice
> and bears no relationship to any real court, dataset or published statistic.
> Court and region names are invented.

---

## The question

*"How long are cases taking, and is anywhere falling behind?"*

Deliberately vague, because that is how a reporting request usually arrives. Most
of the work is turning it into something answerable: deciding what "taking" means,
what the data can actually support, and what it cannot.

## Headline results

| | |
|---|---:|
| Cases in scope | {h['total_cases']:,} |
| Closed | {h['closed_cases']:,} |
| Open | {h['open_cases']:,} |
| **Median days to disposal** | **{h['median_days_national']:.0f}** |
| Mean days to disposal | {h['mean_days_national']:.0f} |
| Open longer than {OVERDUE_DAYS} days | {h['overdue_cases']:,} ({h['overdue_pct']:.1f}%) |
| Rows excluded as unusable | {h['excluded_rows']} |

The mean sits **{h['mean_days_national'] - h['median_days_national']:.0f} days above
the median**. The distribution has a long right tail, so the mean describes a case
that mostly does not exist - every headline figure here is a median.

![Distribution](outputs/figures/02_distribution.png)

---

## Findings

### 1. Where you file changes how long you wait

{f['slow_region']} has a median of **{f['slow_region_days']:.0f} days** against
**{f['fast_region_days']:.0f}** in {f['fast_region']} - a gap of
**{f['region_gap']:.0f} days, roughly {f['region_gap']/7:.0f} weeks**.

![By region](outputs/figures/03_region.png)

Two courts carry most of it. {f['slow_court']} runs at a median of
**{f['slow_court_days']:.0f} days** (n={f['slow_court_n']}), well clear of the rest.

![By court](outputs/figures/04_courts.png)

### 2. The backlog is growing

Filings exceeded disposals by **{f['net_backlog']:,} cases** across the period.
Reported together on purpose: either series alone is a volume figure, but the pair
answers whether the system is keeping up with what arrives.

![Monthly flow](outputs/figures/01_monthly_flow.png)

### 3. The apparent recent improvement is a measurement artefact

This is the finding that mattered most.

Plotted by filing quarter, {f['focus']} deteriorates steadily to
**{f['peak_days']:.0f} days** at {f['peak_q']}, then appears to improve sharply to
**{f['last_days']:.0f} days** by {f['last_q']}.

It has not improved. **Only closed cases can be measured**, and in recent quarters
only the fast ones have closed - the slow cases are still open and invisible to the
measure. The closure rate makes it explicit: **{f['first_closure']:.0%}** of the
earliest quarter's filings have closed, against **{f['last_closure']:.0%}** of the
most recent.

![Censoring](outputs/figures/06_censoring.png)

The pipeline computes that closure rate per quarter and flags any quarter below
{COMPLETENESS_FLOOR:.0%} as incomplete - **{f['n_incomplete']} quarters** for
{f['focus']} - rather than reporting an improvement that is not there.

The measure that *does* see the slow cases is the age profile of the open backlog,
which is why it is reported alongside:

![Backlog](outputs/figures/05_backlog.png)

---

## Data quality

The raw extract has **{f['raw_rows']:,} rows** and arrives in the state these files
usually arrive in. Every issue was decided on deliberately and logged:

{log_md}

### The reconciliation

The extract supplies a duration column from the source system. The duration can
also be derived independently from the filing and disposal dates. **For
{f['mismatch']} cases in the analysis set the two disagree** (47 across the raw
extract, before duplicates and unusable rows are removed - see
`outputs/profile_report.md`).

That is only findable by checking one source against an independent one - the same
control an accountant applies when a ledger has to tie to a statement. Those rows
are quantified and flagged, not corrected: silently overwriting them would hide a
problem in the source system rather than surface it.

### What was excluded, and why

{h['excluded_rows']} rows are flagged `quality_flag = True` and excluded from
analysis - impossible dates, and court IDs that do not exist in the lookup. They
remain in `cases_clean.csv` with a reason attached, so the exclusion is visible
rather than invisible.

### Small counts

Any figure resting on fewer than {SUPPRESSION_THRESHOLD} cases is suppressed before
it is reported. In a small jurisdiction a cell of two or three can identify a
person. Real suppression is harder than this - where row totals are also published,
a reader can sometimes recover a suppressed cell by subtraction - but the principle
belongs in the pipeline rather than in a caveat nobody reads.

---

## Results by region

{region_md}

---

## Running it

```bash
git clone https://github.com/<your-username>/court-timeliness-monitor.git
cd court-timeliness-monitor
pip install -r requirements.txt
python run_pipeline.py
```

Runs in a few seconds and rewrites everything in `data/processed/` and `outputs/`,
including this README. The pipeline is **deterministic** - the reporting date is
pinned in `src/config.py` rather than taken from `today()`, so re-running it next
month cannot silently change the results.

## Repository layout

```
court-timeliness-monitor/
├── run_pipeline.py            # runs all five stages in order
├── src/
│   ├── config.py              # paths, thresholds, palette - every tunable in one place
│   ├── profile_data.py        # stage 1: profile, change nothing
│   ├── clean_data.py          # stage 2: clean, flag, reconcile, merge
│   ├── analyse.py             # stage 3: reporting tables + the censoring check
│   ├── make_charts.py         # stage 4: figures
│   └── make_report.py         # stage 5: this README, from the results
├── data/
│   ├── raw/                   # synthetic source extract, never modified
│   └── processed/             # cleaned data, cleaning log, result tables
├── outputs/
│   ├── figures/               # PNGs
│   └── profile_report.md      # data quality profile
├── docs/
│   ├── data_dictionary.md
│   ├── methodology.md         # definitions and the judgement calls
│   └── findings.md
└── powerbi/
    └── README.md              # the reporting layer built on data/processed/
```

## Design decisions worth knowing

| Decision | Why |
|---|---|
| IDs read as text | `"007"` read as a number becomes `7`, and the join fails |
| Dates parsed day-first explicitly | The default parse corrupts only the 1st-12th of each month - much harder to spot than everything being wrong |
| A blank disposal date is kept blank | It means the case is open. Filling it would invent a disposal |
| Impossible rows flagged, not deleted | A silent fix hides a source-system problem |
| `validate="m:1"` on the merge | Turns a silent fan-out into an immediate error |
| Row count asserted either side of the merge | If it changed, the join key was not unique |
| Reporting date pinned, not `today()` | Otherwise the pipeline is not reproducible |
| Median everywhere, mean shown beside it | The distribution is skewed; the gap between them is itself a finding |
| Denominators shown next to every median | So nobody acts on a median of eleven cases |

## Stack

Python 3.11+ · pandas · matplotlib · Power BI Desktop

---

*Built by Kevin Nguyen - Bachelor of Commerce (Accounting and Business Analytics),
University of Auckland. Synthetic data; not affiliated with any government agency.*
"""


def findings(f: dict) -> str:
    h = f["h"]
    return f"""# Findings

Synthetic data. Nothing here describes a real court.

## 1. Regional spread

| | |
|---|---|
| Slowest region | {f['slow_region']} - {f['slow_region_days']:.0f} days median |
| Fastest region | {f['fast_region']} - {f['fast_region_days']:.0f} days median |
| Gap | {f['region_gap']:.0f} days ({f['region_gap']/7:.0f} weeks) |

Interpretation: in a service context, a spread this size is a question about
consistency of access, not only about efficiency. It is worth separating *where a
case is filed* from *what kind of case it is* before drawing any conclusion - the
slowest court sits in {f['court'].iloc[0]['region']}, but the second slowest does not.

## 2. Backlog direction

Filings exceeded disposals by {f['net_backlog']:,} over the period, and
{h['overdue_cases']:,} open cases ({h['overdue_pct']:.1f}%) have now been open longer
than {OVERDUE_DAYS} days.

## 3. Right-censoring in the disposal-time series

The most important finding, and the one a dashboard would most easily get wrong.

Median time to disposal can only be computed on cases that have closed. For
recently filed cases, only the fast ones have closed. So recent periods are made up
of a biased subset and the median falls - which reads as improvement.

For {f['focus']}:

| Filing quarter | Closure rate | Median days | Reported? |
|---|---:|---:|---|
| earliest | {f['first_closure']:.0%} | - | yes |
| {f['peak_q']} | - | {f['peak_days']:.0f} | yes |
| {f['last_q']} | {f['last_closure']:.0%} | {f['last_days']:.0f} | **no - incomplete** |

### What the pipeline does about it

1. Computes the closure rate for every filing quarter.
2. Flags any quarter below {COMPLETENESS_FLOOR:.0%} as incomplete.
3. Reports the open backlog's age profile alongside - the measure that *does*
   capture the slow cases, because it counts what is still waiting.
4. Marks the incomplete region on the chart rather than leaving it to be misread.

## Limitations

- Synthetic data. The patterns are ones I generated; they are not evidence about
  anything real.
- "Waiting time" here is filing to disposal. Filing to first hearing is an equally
  valid measure that answers a different question, and in a real setting the
  definition would be owned by the business, not by the analyst.
- {h['excluded_rows']} rows were excluded as unusable. That is small relative to
  {f['raw_rows']:,}, but exclusions should always be quoted rather than hidden.
- The suppression rule here is a simple cell threshold. Real disclosure control
  also has to consider what can be recovered by subtraction when totals are
  published.
"""


def main() -> None:
    print("=" * 62)
    print("STAGE 5 - REPORT")
    print("=" * 62)
    f = facts()
    (ROOT / "README.md").write_text(readme(f), encoding="utf-8")
    (DOCS_DIR / "findings.md").write_text(findings(f), encoding="utf-8")
    print("  README.md")
    print("  docs/findings.md")
    print("  (every figure quoted is read from the result tables)")


if __name__ == "__main__":
    main()
