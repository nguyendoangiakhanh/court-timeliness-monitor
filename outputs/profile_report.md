# Data quality profile

Produced by `src/profile_data.py` against the raw extract. 
No data is modified at this stage.

## Shape

- 4,238 rows, 7 columns
- 4,200 unique case IDs
- 12 courts in the lookup table

## Issues found

| Issue | Count | Interpretation |
|---|---:|---|
| Duplicate case IDs | 38 | Repeated keys; some pairs disagree on status |
| Distinct `case_type` values | 21 | Should be 4; casing, whitespace, abbreviations |
| Distinct `status` values | 7 | Should be 2 |
| Blank `disposed_date` | 908 | **Not missing data** — the case is still open |
| Court ID missing or not in lookup | 31 | Cannot be attributed to a court or region |
| Disposed before filed | 18 | Impossible; flagged, not corrected |
| Filed in the future | 5 | Impossible; flagged, not corrected |
| `reported_days` not numeric | 0 | Whitespace, `N/A`, `-` |
| **`reported_days` disagrees with calculated duration** | **47** | **Reconciliation exception — see below** |

## The reconciliation

The extract supplies a duration column (`reported_days`) from the source system. 
The duration can also be derived independently from `filed_date` and `disposed_date`. 
For **47 cases the two do not agree**.

This is only findable by checking one source against an independent one — the same 
control an accountant applies when a ledger has to tie to a statement. These rows are 
quantified and flagged, not corrected: silently overwriting them would hide a problem 
in the source system.

## Null rate by column (%)

| Column | Null % |
|---|---:|
| `case_id` | 0.0 |
| `court_id` | 0.2 |
| `case_type` | 0.0 |
| `filed_date` | 0.0 |
| `disposed_date` | 21.4 |
| `status` | 0.0 |
| `reported_days` | 23.7 |
