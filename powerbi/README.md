# Power BI reporting layer

The Python pipeline produces the clean, analysis-ready tables. This is the
reporting layer built on top of them — the part a non-technical user opens.

Build it yourself against `../data/processed/`; a `.pbix` is not committed
(binary files are poor repository citizens, and it would go stale the moment the
pipeline is re-run).

---

## Sources

| Table | File | Role |
|---|---|---|
| `Cases` | `data/processed/cases_clean.csv` | Fact — one row per case |
| `Courts` | `data/processed/courts_clean.csv` | Dimension |
| `CleaningLog` | `data/processed/cleaning_log.csv` | Data-quality page |
| `Calendar` | created in DAX | Date dimension |

## Model

A star schema: one fact table, dimensions joined one-to-many into it, single
filter direction throughout.

```
        Calendar                 Courts
            |                       |
            └──────  Cases  ────────┘
                    (fact)
```

```dax
Calendar = CALENDAR(DATE(2024,7,1), DATE(2026,12,31))
```

Add `Year`, `Month name`, `Month number`, `Quarter`. **Mark as date table**, and
sort `Month name` by `Month number` — otherwise every chart runs April, August,
December.

Relationships:

- `Courts[court_id]` → `Cases[court_id]`, one-to-many, single direction
- `Calendar[Date]` → `Cases[filed_date]`, one-to-many, single direction

In Power Query, rename every column to what a stakeholder would call it —
`Waiting days`, not `waiting_days`. These are the labels on every visual.

## Measures

```dax
Total Cases      = COUNTROWS(Cases)
Active Cases     = CALCULATE([Total Cases], Cases[is_open] = TRUE())
Disposed Cases   = CALCULATE([Total Cases], Cases[is_open] = FALSE())

Median Days      = MEDIAN(Cases[waiting_days])
Mean Days        = AVERAGE(Cases[waiting_days])

Overdue Cases    = CALCULATE([Total Cases], Cases[overdue] = TRUE())
Overdue %        = DIVIDE([Overdue Cases], [Active Cases], 0)

Excluded Rows    = CALCULATE([Total Cases], Cases[quality_flag] = TRUE())
Duration Mismatches = CALCULATE([Total Cases], Cases[duration_mismatch] = TRUE())

Median vs National =
    [Median Days] - CALCULATE([Median Days], ALL(Courts))
```

`DIVIDE` rather than `/` throughout: it handles division by zero instead of
breaking the visual.

Two of these are deliberate. **Mean beside median** — where they diverge the
distribution is skewed and the mean is the wrong headline. **`Excluded Rows`** —
putting your own exclusions on the report as a number, rather than hiding them.

## Pages

### 1. Overview — *is anything wrong?*

- Cards: Active Cases · Median Days · Overdue % · Cases Filed, each against the
  prior period
- Line: filings and disposals by month, on one chart
- Bar: median days by region, sorted
- Histogram: distribution of waiting days — this is what justifies reporting a
  median rather than a mean
- Slicers: date, region, case type. Three, not eight
- Footer: the definition of "waiting days", and the words **synthetic data**

### 2. Exceptions — *which ones?*

- Horizontal bar: Overdue % by court, worst first
- Matrix: court × age band, conditionally formatted
- Drill-through to a case list, filtered to whichever court was clicked
- `n` shown beside every median, so nobody acts on a median of eleven

### 3. Data quality

- `CleaningLog` as a table
- Cards: `Excluded Rows`, `Duration Mismatches`
- A note on the right-censoring limitation

Most people skip this page. It is the one that turns "I made a dashboard" into "I
can tell you exactly what my numbers rest on".

## Accessibility

Public-sector reporting carries obligations a commercial dashboard may not:

- Alt text on every visual; sensible tab order
- Never colour alone — pair it with a label or position
- Contrast that passes; no light grey on white
- Plain-language names, no internal acronyms
- The measure definition visible on the page, because most disagreements about a
  number turn out to be disagreements about what it counts

## The limitation to put on the page

Median time to disposal is computed on closed cases only. For recently filed
cases, only the fast ones have closed, so recent periods understate delay. The
pipeline flags quarters below 80% closure as incomplete — the report should either
exclude them from the trend or mark them visibly, and always show the open backlog
age profile alongside.
