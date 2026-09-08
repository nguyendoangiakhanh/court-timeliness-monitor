# Methodology

How each figure in this project is defined, and the judgement calls behind it.
Synthetic data throughout — nothing here describes a real court.

## Measure definitions

| Measure | Definition | Population |
|---|---|---|
| **Waiting days** | Calendar days from `filed_date` to `disposed_date` | Closed cases only |
| **Days open** | Calendar days from `filed_date` to the reporting date | Open cases only |
| **Median days to disposal** | Median of waiting days | Closed, unflagged cases |
| **Overdue** | Open longer than 365 days | Open, unflagged cases |
| **Overdue %** | Overdue cases ÷ open cases | Per region or court |
| **Closure rate** | Cases closed ÷ cases filed, per filing quarter | All cases in that quarter |
| **Net change** | Filings − disposals, per month | All cases |

**Grain.** One row of `cases_clean.csv` is one case. Result tables state their own
grain: `summary_by_region` is one row per region, `monthly_flow` is one row per
month, `disposal_time_by_quarter` is one row per region per filing quarter.

## Judgement calls

### Filing to disposal, not filing to first hearing

"Waiting time" could reasonably mean either, and they answer different questions —
one is about how long until you are heard, the other about how long until it is
over. Filing to disposal was chosen here because the synthetic extract supports it.

**In a real setting this definition would not be the analyst's to make.** It would
be owned by the business, and the first task would be finding out which one is
already in use so a new report does not contradict an existing one.

### Median, not mean

Time-to-disposal has a long right tail. The mean sits above the median, describing
a case that mostly does not exist. Both are computed and reported side by side —
where they diverge sharply, that gap is itself worth showing a stakeholder.

### Denominators are always shown

A median over eleven cases is not something anyone should act on. Showing `n`
beside every median says so without needing a disclaimer.

### Right-censoring

The central methodological problem in this dataset.

Disposal time can only be measured on cases that have closed. For recently filed
cases, only the fast ones have closed — the slow ones are still running and are
invisible to the measure. So the most recent periods consist of a biased subset and
the median falls, which reads as improvement.

The pipeline handles this in three ways:

1. `closure_rate` is computed for every filing quarter.
2. Quarters below 80% closure are marked `complete = False` and are not reported
   as a trend.
3. The open backlog's age profile is reported alongside — that measure *does*
   capture the slow cases, because it counts what is still waiting.

The 80% floor is a choice made for this exercise, not a standard.

### Flag, don't delete

Impossible rows — a disposal before the filing, a filing in the future, a court ID
that does not exist — are marked with `quality_flag` and a reason, and excluded
from analysis. They stay in the file.

Deleting them would make the exclusion invisible. Correcting them would be worse:
it would hide a problem in the source system that somebody needs to know about.

### A blank disposal date is information

It means the case is open. It is not filled, and those cases are excluded from
duration measures and counted separately as backlog. Filling it — with the
reporting date, say — would invent a disposal that never happened.

### Duplicate resolution

38 case IDs appear twice, and some pairs disagree: one row shows the case open, the
other disposed. That is consistent with a superseded extract, so the row carrying a
disposal date is treated as the later and more complete record.

This is a decision, not a rule. It is logged as one.

### Small-count suppression

Any figure resting on fewer than five cases is blanked before reporting. In a small
jurisdiction, a cell of two or three can identify a person.

Real disclosure control is harder than a cell threshold: where row totals are also
published, a reader can sometimes recover a suppressed cell by subtraction. The
threshold used here is illustrative.

## Reconciliation control

The extract supplies `reported_days` from the source system. The pipeline
independently derives the duration from the two date fields and compares them.
47 cases disagree.

This is the analytic equivalent of tying a ledger to an independent statement: you
do not rely on a figure until it agrees with something computed another way. The
mismatches are quantified and flagged in `duration_mismatch`. The calculated
duration is used for analysis, because it can be traced to its inputs.

## Merge validation

`cases.merge(courts, how="left", validate="m:1", indicator=True)`

- `validate="m:1"` raises immediately if the court lookup key is not unique,
  turning a silent fan-out into a loud failure.
- The row count is asserted either side of the merge.
- `indicator=True` identifies the anti-join — cases whose court ID matches nothing.

## Reproducibility

- The reporting date is pinned in `src/config.py`. Using `today()` would mean the
  same code produced different numbers on different days.
- The synthetic data is generated from a fixed random seed.
- The README and findings document are generated from the result tables, so a
  figure quoted in prose cannot drift from the data behind it.

## Chart conventions

- One y-axis per chart. Never two scales.
- Categorical colours from validated slots — blue `#2a78d6` and orange `#eb6834`,
  which clear colour-vision-deficiency separation thresholds against each other and
  against the chart surface.
- Sequential shading (light → dark, one hue) for the ordered age bands.
- A legend wherever two series share a chart, plus direct labels, so identity is
  never carried by colour alone.
- Recessive grid and axes; values rounded to the decision, not to the float.
- Every axis label names a value the chart actually reaches.
