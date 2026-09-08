# Findings

Synthetic data. Nothing here describes a real court.

## 1. Regional spread

| | |
|---|---|
| Slowest region | Eastern — 157 days median |
| Fastest region | Northern — 108 days median |
| Gap | 49 days (7 weeks) |

Interpretation: in a service context, a spread this size is a question about
consistency of access, not only about efficiency. It is worth separating *where a
case is filed* from *what kind of case it is* before drawing any conclusion — the
slowest court sits in Eastern, but the second slowest does not.

## 2. Backlog direction

Filings exceeded disposals by 881 over the period, and
198 open cases (22.3%) have now been open longer
than 365 days.

## 3. Right-censoring in the disposal-time series

The most important finding, and the one a dashboard would most easily get wrong.

Median time to disposal can only be computed on cases that have closed. For
recently filed cases, only the fast ones have closed. So recent periods are made up
of a biased subset and the median falls — which reads as improvement.

For Eastern:

| Filing quarter | Closure rate | Median days | Reported? |
|---|---:|---:|---|
| earliest | 94% | — | yes |
| 2025Q3 | — | 191 | yes |
| 2026Q2 | 21% | 94 | **no — incomplete** |

### What the pipeline does about it

1. Computes the closure rate for every filing quarter.
2. Flags any quarter below 80% as incomplete.
3. Reports the open backlog's age profile alongside — the measure that *does*
   capture the slow cases, because it counts what is still waiting.
4. Marks the incomplete region on the chart rather than leaving it to be misread.

## Limitations

- Synthetic data. The patterns are ones I generated; they are not evidence about
  anything real.
- "Waiting time" here is filing to disposal. Filing to first hearing is an equally
  valid measure that answers a different question, and in a real setting the
  definition would be owned by the business, not by the analyst.
- 50 rows were excluded as unusable. That is small relative to
  4,200, but exclusions should always be quoted rather than hidden.
- The suppression rule here is a simple cell threshold. Real disclosure control
  also has to consider what can be recovered by subtraction when totals are
  published.
