"""Stage 1 — profile the raw extract without changing it.

Prints a data-quality report and writes it to outputs/profile_report.md.

The rule this stage exists to enforce: understand the file before touching it.
Nothing here modifies the data.
"""

from __future__ import annotations

import pandas as pd

from config import (AS_AT, CASES_RAW, COURTS_RAW, DATE_FORMAT, NA_VALUES,
                    OUTPUT_DIR)


def load_raw() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read both source files with explicit types.

    IDs are read as text on purpose. They are labels, not quantities: reading
    them as numbers strips leading zeros ("007" -> 7) and breaks the join.
    Dates are parsed day-first; the default US-style parse would silently
    corrupt every date from the 1st to the 12th of a month.
    """
    cases = pd.read_csv(
        CASES_RAW,
        dtype={"case_id": "string", "court_id": "string"},
        na_values=NA_VALUES,
        keep_default_na=True,
    )
    for col in ("filed_date", "disposed_date"):
        cases[col] = pd.to_datetime(cases[col], format=DATE_FORMAT, errors="coerce")

    courts = pd.read_csv(COURTS_RAW, dtype={"court_id": "string"})
    return cases, courts


def profile(cases: pd.DataFrame, courts: pd.DataFrame) -> dict:
    """Return the data-quality facts. Computes nothing it does not report."""
    reported = pd.to_numeric(cases["reported_days"].astype("string").str.strip(),
                             errors="coerce")
    calculated = (cases["disposed_date"] - cases["filed_date"]).dt.days

    both_known = reported.notna() & calculated.notna()
    mismatch = both_known & (reported != calculated)

    orphan_mask = ~cases["court_id"].isin(courts["court_id"])

    return {
        "rows": len(cases),
        "columns": cases.shape[1],
        "unique_case_ids": int(cases["case_id"].nunique()),
        "duplicate_case_id_rows": int(cases.duplicated(subset=["case_id"]).sum()),
        "case_type_variants": int(cases["case_type"].nunique(dropna=True)),
        "status_variants": int(cases["status"].nunique(dropna=True)),
        "open_cases": int(cases["disposed_date"].isna().sum()),
        "orphan_or_missing_court": int(orphan_mask.sum()),
        "disposed_before_filed": int((calculated < 0).sum()),
        "filed_in_future": int((cases["filed_date"] > pd.Timestamp(AS_AT)).sum()),
        "reported_days_uncoercible": int(
            cases["reported_days"].notna().sum() - reported.notna().sum()
        ),
        "reported_vs_calculated_mismatch": int(mismatch.sum()),
        "courts_in_lookup": len(courts),
        "null_pct": (cases.isna().mean() * 100).round(1).to_dict(),
    }


def to_markdown(p: dict) -> str:
    lines = [
        "# Data quality profile",
        "",
        "Produced by `src/profile_data.py` against the raw extract. ",
        "No data is modified at this stage.",
        "",
        "## Shape",
        "",
        f"- {p['rows']:,} rows, {p['columns']} columns",
        f"- {p['unique_case_ids']:,} unique case IDs",
        f"- {p['courts_in_lookup']} courts in the lookup table",
        "",
        "## Issues found",
        "",
        "| Issue | Count | Interpretation |",
        "|---|---:|---|",
        f"| Duplicate case IDs | {p['duplicate_case_id_rows']} | Repeated keys; some pairs disagree on status |",
        f"| Distinct `case_type` values | {p['case_type_variants']} | Should be 4; casing, whitespace, abbreviations |",
        f"| Distinct `status` values | {p['status_variants']} | Should be 2 |",
        f"| Blank `disposed_date` | {p['open_cases']:,} | **Not missing data** — the case is still open |",
        f"| Court ID missing or not in lookup | {p['orphan_or_missing_court']} | Cannot be attributed to a court or region |",
        f"| Disposed before filed | {p['disposed_before_filed']} | Impossible; flagged, not corrected |",
        f"| Filed in the future | {p['filed_in_future']} | Impossible; flagged, not corrected |",
        f"| `reported_days` not numeric | {p['reported_days_uncoercible']} | Whitespace, `N/A`, `-` |",
        f"| **`reported_days` disagrees with calculated duration** | **{p['reported_vs_calculated_mismatch']}** | **Reconciliation exception — see below** |",
        "",
        "## The reconciliation",
        "",
        "The extract supplies a duration column (`reported_days`) from the source system. ",
        "The duration can also be derived independently from `filed_date` and `disposed_date`. ",
        f"For **{p['reported_vs_calculated_mismatch']} cases the two do not agree**.",
        "",
        "This is only findable by checking one source against an independent one — the same ",
        "control an accountant applies when a ledger has to tie to a statement. These rows are ",
        "quantified and flagged, not corrected: silently overwriting them would hide a problem ",
        "in the source system.",
        "",
        "## Null rate by column (%)",
        "",
        "| Column | Null % |",
        "|---|---:|",
    ]
    for col, pct in p["null_pct"].items():
        lines.append(f"| `{col}` | {pct} |")
    lines.append("")
    return "\n".join(lines)


def main() -> dict:
    cases, courts = load_raw()
    p = profile(cases, courts)

    print("=" * 62)
    print("STAGE 1 — PROFILE")
    print("=" * 62)
    print(f"  rows                              {p['rows']:>8,}")
    print(f"  unique case ids                   {p['unique_case_ids']:>8,}")
    print(f"  duplicate case id rows            {p['duplicate_case_id_rows']:>8}")
    print(f"  case_type variants                {p['case_type_variants']:>8}")
    print(f"  status variants                   {p['status_variants']:>8}")
    print(f"  open cases (blank disposed_date)  {p['open_cases']:>8,}")
    print(f"  orphan / missing court_id         {p['orphan_or_missing_court']:>8}")
    print(f"  disposed before filed             {p['disposed_before_filed']:>8}")
    print(f"  filed in the future               {p['filed_in_future']:>8}")
    print(f"  reported_days not numeric         {p['reported_days_uncoercible']:>8}")
    print(f"  reported vs calculated mismatch   {p['reported_vs_calculated_mismatch']:>8}   <-- reconciliation")

    out = OUTPUT_DIR / "profile_report.md"
    out.write_text(to_markdown(p), encoding="utf-8")
    print(f"\n  written: {out.relative_to(out.parents[1])}")
    return p


if __name__ == "__main__":
    main()
