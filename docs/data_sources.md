# Real public data sources

The pipeline in this repository currently runs on **synthetic** data. This
document lists the real, published, openly available datasets it can be pointed
at instead, and what each one actually contains.

Verified against the Ministry's published data-tables page, December 2025 release.

---

## Before anything: check the licence

The data-tables page does not state reuse terms inline. New Zealand government
data is generally released under [NZGOAL](https://www.digital.govt.nz/standards-and-guidance/nzgoal/),
which defaults to a Creative Commons licence, but **confirm it on the Ministry's
copyright page before republishing anything**, and cite the source and release
date in any output.

Checking the licence before reusing public data is not bureaucracy. It is the
first thing a public-sector analyst does, and being able to say you did it is
worth more in an interview than the analysis.

---

## New Zealand Ministry of Justice — Justice Statistics data tables

Landing page:
<https://www.justice.govt.nz/justice-sector-policy/research-data/justice-statistics/data-tables/>

All files are `.xlsx`, updated roughly six-monthly. Filenames carry the release
month, so the URLs below will change at the next release — always take the link
from the landing page rather than hard-coding it.

### The most useful for a BI portfolio project

| Dataset | Size | What is in it | Good for |
|---|---|---|---|
| **All finalised charges and convicted charges** | 284 KB | Charges by offence type, outcome and sentence type, over time | Trend and composition analysis. The best general-purpose starting point |
| **People with finalised charges** | 264 KB | People charged and convicted, by offence, outcome, sentence and demographics | Equity and access analysis |
| **Family Court applications** | 174 KB | Substantive applications by case type and court location | **Closest to a regional-access question** |
| **Legal aid** | 75 KB | Grants and expenditure | Resourcing against demand — pairs well with charge volumes |
| **Collections** | 50 KB | Fines and reparations imposed and paid | A clean two-series "imposed vs recovered" analysis |
| **Children and young people in the Youth Court** | 320 KB | Youth Court finalised charges and demographics | Youth justice focus |
| **Protection Order applications** | 279 KB | Applications filed, those involving children, applicant and respondent demographics | Family violence focus — handle with care |

Also published: homicide, sexual, family violence, violent, serious, firearm,
drug, cannabis, methamphetamine, DUI, strangulation, gangs, three-strikes,
harmful digital communications, name suppression, discharge without conviction,
outcomes for mentally impaired persons, remand and bail, adoptions, family
violence programmes.

### What is **not** published at case level

Court **waiting times and case-level timeliness** — the theme this repository's
synthetic data models — are not in the open data tables. The tables are
**aggregate counts of finalised charges**, not one row per case with a filing
and disposal date.

The Courts of New Zealand publish some annual workload statistics
(<https://www.courtsofnz.govt.nz/publications/annual-statistics>), largely as
PDF, and Stats NZ carries related series in Aotearoa Data Explorer.

**This matters for the project.** Real MOJ data will not answer "how long are
cases taking". It answers questions about volume, composition, outcome and
demographics. If you switch to real data, the question has to change with it —
which is itself the correct lesson: *the data you have determines the question
you can ask, not the other way round.*

---

## Other relevant open sources

| Source | What | Link |
|---|---|---|
| **Stats NZ — Aotearoa Data Explorer** | Crime and justice series, machine-readable | <https://www.stats.govt.nz/> |
| **NZ Crime & Victims Survey** | Victimisation, with full documentation and data | <https://www.justice.govt.nz/justice-sector-policy/research-data/nzcvs/> |
| **data.govt.nz** | The whole-of-government catalogue | <https://catalogue.data.govt.nz/> |
| **UK MOJ — Criminal Court Statistics Quarterly** | Genuine case-level **timeliness** data, in CSV, thoroughly documented | <https://www.gov.uk/government/collections/criminal-court-statistics> |

The UK series is worth knowing about: it is the closest real public analogue to
the waiting-times question, it is published as CSV rather than spreadsheet, and
its methodology notes are unusually good. Different jurisdiction, so it answers
nothing about New Zealand — but as a modelling reference it is instructive.

---

## Using a real workbook with this repository

The Ministry's workbooks are built to be read by people, not machines: title
blocks above the header, years spread across columns, footnote markers and
suppression symbols inside numeric columns, merged cells, and note rows at the
bottom.

`src/load_moj_xlsx.py` handles all of that generically rather than hard-coding a
layout that breaks at the next release.

```bash
# 1. Download a workbook from the landing page into data/raw/

# 2. See what is in it — sheets, detected header rows, period columns
python src/load_moj_xlsx.py data/raw/<file>.xlsx

# 3. Tidy one sheet and look at it
python src/load_moj_xlsx.py data/raw/<file>.xlsx --sheet "Table 1"

# 4. Unpivot every wide sheet into one long CSV
python src/load_moj_xlsx.py data/raw/<file>.xlsx --tidy-all
```

What the loader does that a naive `read_excel` does not:

- **Detects the header row** instead of assuming row 0, so title blocks do not
  become column names.
- **Unpivots year columns to long form.** A wide table breaks every time a new
  year is added; long survives. This is the single most common fix needed before
  a spreadsheet can drive a chart.
- **Separates suppression markers from numbers.** `S`, `C`, `..`, `-` and `*` are
  *meaning*, not missingness. Coercing them to null silently converts "withheld
  because the count was too small" into "we do not know", which is a different
  statement. The loader keeps the reason in its own column.
- **Forward-fills dimension columns** to undo merged cells.
- **Drops trailing note rows** without dropping data.

That suppression point is worth carrying into an interview. It is exactly the
kind of detail that separates someone who has handled published government
statistics from someone who has only handled clean CSVs.
