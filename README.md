# Court Timeliness Monitor

**An end-to-end analytics pipeline on synthetic public-sector data - Python for
cleaning and analysis, Power BI for the reporting layer.**

> **The data in this repository is synthetic.** It was generated for practice and
> bears no relationship to any real court, dataset or published statistic. Court
> and region names are invented.

---

## The question

*"How long are cases taking, and is anywhere falling behind?"*

Deliberately vague, because that is how a reporting request usually arrives. Most
of the work is turning it into something answerable: deciding what "taking" means,
what the data can actually support, and what it cannot.

## Headline results

| | |
|---|---:|
| Cases in scope | 4,200 |
| Closed | 3,312 |
| Open | 888 |
| **Median days to disposal** | **123** |
| Mean days to disposal | 146 |
| Open longer than 365 days | 198 (22.3%) |
| Rows excluded as unusable | 50 |

The mean sits **23 days above
the median**. The distribution has a long right tail, so the mean describes a case
that mostly does not exist - every headline figure here is a median.

```python
w = cases.loc[~cases.quality_flag & cases.waiting_days.notna(), "waiting_days"]

fig, ax = plt.subplots(figsize=(9, 4))
ax.hist(w, bins=45, edgecolor="white")
ax.axvline(w.median(), lw=2, label=f"Median {w.median():.0f} days")
ax.axvline(w.mean(), lw=2, ls="--", label=f"Mean {w.mean():.0f} days")
ax.set_xlabel("Days from filing to disposal"); ax.set_ylabel("Cases")
ax.legend(frameon=False)
```

<img width="1156" height="637" alt="image" src="https://github.com/user-attachments/assets/64c6122a-ea7a-4446-a7c1-3ab2c83da177" />

---

## Findings

### 1. Where you file changes how long you wait

Eastern has a median of **157 days** against
**108** in Northern - a gap of
**49 days, roughly 7 weeks**.

Two courts carry most of it. Cape Lawson District Court runs at a median of
**187 days** (n=247), well clear of the rest.

```python
region = pd.read_csv("data/processed/summary_by_region.csv")
region = region.dropna(subset=["median_days"]).sort_values("median_days")

fig, ax = plt.subplots(figsize=(8, 3.5))
bars = ax.barh(region.region, region.median_days)
ax.bar_label(bars, fmt="%.0f", padding=4)
ax.set_xlabel("Median days to disposal")
```

<img width="1023" height="572" alt="image" src="https://github.com/user-attachments/assets/53160a64-02b0-4b0b-b08d-b760fb50536b" />
<!-- PASTE SCREENSHOT: median by court -->

### 2. The backlog is growing

Filings exceeded disposals by **881 cases** across the period.
Reported together on purpose: either series alone is a volume figure, but the pair
answers whether the system is keeping up with what arrives.

```python
monthly = pd.read_csv("data/processed/monthly_flow.csv").sort_values("month")

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(monthly.month, monthly.filings,  marker="o", lw=2, label="Filed")
ax.plot(monthly.month, monthly.disposals, marker="o", lw=2, label="Disposed")
ax.set_ylabel("Cases"); ax.legend(frameon=False)
plt.xticks(rotation=45, ha="right")
```

<img width="1156" height="637" alt="image" src="https://github.com/user-attachments/assets/c5640293-624f-44d1-90d3-9397cf1a0521" />

### 3. The apparent recent improvement is a measurement artefact

This is the finding that mattered most.

Plotted by filing quarter, Eastern deteriorates steadily to
**191 days** at 2025Q3, then appears to improve sharply to
**94 days** by 2026Q2.

It has not improved. **Only closed cases can be measured**, and in recent quarters
only the fast ones have closed - the slow cases are still open and invisible to the
measure. The closure rate makes it explicit: **94%** of the
earliest quarter's filings have closed, against **21%** of the
most recent.

The pipeline computes that closure rate per quarter and flags any quarter below
80% as incomplete - **3 quarters** for
Eastern - rather than reporting an improvement that is not there.

```python
q = df.groupby(["filed_quarter", "region"]).agg(
        filed=("case_id", "nunique"),
        closed=("disposed_date", "count"),
        median_days=("waiting_days", "median"),
    ).reset_index()

# share of each quarter's filings that have actually closed
q["closure_rate"] = q.closed / q.filed

# below this, the median is computed from a biased subset - the fast cases only
q["complete"] = q.closure_rate >= 0.80
```

<!-- PASTE SCREENSHOT: censoring / closure rate -->

The measure that *does* see the slow cases is the age profile of the open backlog,
which is why it is reported alongside:

```python
backlog = pd.read_csv("data/processed/backlog_age_profile.csv")
pivot = backlog.pivot(index="region", columns="age_band",
                      values="open_cases").fillna(0)
pivot = pivot[["0-3 months", "3-12 months", "12+ months"]]

fig, ax = plt.subplots(figsize=(9, 4))
left = pivot.iloc[:, 0] * 0
for col in pivot.columns:
    ax.barh(pivot.index, pivot[col], left=left, label=col)
    left = left + pivot[col]
ax.set_xlabel("Open cases"); ax.legend(frameon=False)
```

<img width="1091" height="572" alt="image" src="https://github.com/user-attachments/assets/c05d3e0c-a170-44db-a010-8669380aaaf6" />

---

## Data quality

The raw extract has **4,200 rows** and arrives in the state these files
usually arrive in. Every issue was decided on deliberately and logged:

| issue                                                                 |   rows_affected | decision                                                                        | reason                                                                           |
|:----------------------------------------------------------------------|----------------:|:--------------------------------------------------------------------------------|:---------------------------------------------------------------------------------|
| `case_type` had 21 distinct values                                    |              17 | Trimmed, title-cased and mapped variants -> 4 canonical values                  | Casing, whitespace and abbreviations only; no genuine category was merged        |
| `status` had 7 distinct values                                        |               5 | Trimmed, title-cased and mapped variants -> 2 canonical values                  | Casing, whitespace and abbreviations only; no genuine category was merged        |
| Duplicate case IDs                                                    |              38 | Kept the more complete record per case ID                                       | Pairs disagreed on status; the row with a disposal date is the later extract     |
| Rows where disposed before filed                                      |              18 | Flagged and excluded from analysis; retained in the file                        | Correcting silently would hide a source-system problem                           |
| Rows where filed in the future                                        |               5 | Flagged and excluded from analysis; retained in the file                        | Correcting silently would hide a source-system problem                           |
| Rows where court_id not in lookup                                     |              31 | Flagged and excluded from analysis; retained in the file                        | Correcting silently would hide a source-system problem                           |
| `reported_days` disagrees with the duration calculated from the dates |              47 | Quantified and flagged; the calculated duration is used for analysis            | Only findable by checking the source figure against an independent recomputation |
| Cases with no matching court in the lookup                            |              31 | Left join retained them; already flagged and excluded from court-level analysis | An anti-join finding worth reporting to the data owner, not deleting             |

<img width="1164" height="702" alt="image" src="https://github.com/user-attachments/assets/9764897b-1f42-49b1-857f-2f2fa793544e" />

### The reconciliation

The extract supplies a duration column from the source system. The duration can
also be derived independently from the filing and disposal dates. **For
29 cases in the analysis set the two disagree** (47 across the raw
extract, before duplicates and unusable rows are removed - see
`outputs/profile_report.md`).

```python
df["reported_days"] = pd.to_numeric(
    df.reported_days.astype("string").str.strip(), errors="coerce")
df["waiting_days"]  = (df.disposed_date - df.filed_date).dt.days

both = df.reported_days.notna() & df.waiting_days.notna()
df["duration_mismatch"] = both & (df.reported_days != df.waiting_days)
```

That is only findable by checking one source against an independent one - the same
control an accountant applies when a ledger has to tie to a statement. Those rows
are quantified and flagged, not corrected: silently overwriting them would hide a
problem in the source system rather than surface it.

### The merge, with its assumption asserted

```python
rows_before = len(cases)
merged = cases.merge(courts, on="court_id", how="left",
                     validate="m:1",      # raises if the lookup key is not unique
                     indicator=True)      # identifies the anti-join
assert rows_before == len(merged), "merge changed the row count"
```

`validate="m:1"` turns a silent fan-out into an immediate error. The row count is
asserted either side, so if the join duplicated rows the pipeline stops instead of
quietly reporting totals that are three times too big.

### What was excluded, and why

50 rows are flagged `quality_flag = True` and excluded from
analysis - impossible dates, and court IDs that do not exist in the lookup. They
remain in `cases_clean.csv` with a reason attached, so the exclusion is visible
rather than invisible.

```python
checks = [
    (df.disposed_date < df.filed_date,        "disposed before filed"),
    (df.filed_date > AS_AT,                   "filed in the future"),
    (~df.court_id.isin(courts.court_id),      "court_id not in lookup"),
]
for mask, reason in checks:
    df.loc[mask.fillna(False), "quality_reason"] = reason
    df.loc[mask.fillna(False), "quality_flag"] = True
```

### Small counts

Any figure resting on fewer than 5 cases is suppressed before
it is reported. In a small jurisdiction a cell of two or three can identify a
person.

```python
def suppress(series, n):
    return series.where(n >= 5)
```

Real suppression is harder than this - where row totals are also published, a
reader can sometimes recover a suppressed cell by subtraction - but the principle
belongs in the pipeline rather than in a caveat nobody reads.

---

## Results by region

| region   |   closed |   median days |   mean days |   open |   overdue % |
|:---------|---------:|--------------:|------------:|-------:|------------:|
| Eastern  |      534 |           157 |         179 |    186 |        20.4 |
| Central  |      759 |           136 |         161 |    257 |        25.3 |
| Southern |     1125 |           115 |         133 |    252 |        21.4 |
| Northern |      851 |           108 |         131 |    186 |        22   |

---

## Running it

```bash
git clone https://github.com/nguyendoangiakhanh/court-timeliness-monitor.git
cd court-timeliness-monitor
pip install -r requirements.txt
python run_pipeline.py
```

Runs in a few seconds and rewrites everything in `data/processed/` and `outputs/`,
including this README. The pipeline is **deterministic** - the reporting date is
pinned in `src/config.py` rather than taken from `today()`, so re-running it next
month cannot silently change the results.

There is also a Colab notebook at `notebooks/02_colab_charts.ipynb` that clones the
repo, runs the pipeline and renders every chart inline.

## Repository layout

```
court-timeliness-monitor/
|- run_pipeline.py            # runs all five stages in order
|- src/
|  |- config.py               # paths, thresholds, chart style - every tunable in one place
|  |- profile_data.py         # stage 1: profile, change nothing
|  |- clean_data.py           # stage 2: clean, flag, reconcile, merge
|  |- analyse.py              # stage 3: reporting tables + the censoring check
|  |- make_charts.py          # stage 4: figures
|  |- make_report.py          # stage 5: this README, from the results
|  \- load_moj_xlsx.py        # reader for real MOJ published data tables
|- data/
|  |- raw/                    # synthetic source extract, never modified
|  \- processed/              # cleaned data, cleaning log, result tables
|- outputs/
|  |- figures/                # PNGs
|  \- profile_report.md       # data quality profile
|- docs/
|  |- data_dictionary.md
|  |- methodology.md          # definitions and the judgement calls
|  |- data_sources.md         # real public datasets this can be pointed at
|  \- findings.md
|- notebooks/
\- powerbi/
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
| Chart style is a config switch | Presentation is a setting, not something hard-coded through the code |

## Stack

Python 3.11+ | pandas | matplotlib | Power BI Desktop

---

*Built by Kevin Nguyen - Bachelor of Commerce (Accounting and Business Analytics),
University of Auckland. Synthetic data; not affiliated with any government agency.*
