"""Stage 2 — clean the extract, recording every decision.

Design rules followed here:

1. Flag, don't delete. Impossible rows stay in the file with a reason attached,
   so the exclusion is visible rather than invisible.
2. A blank disposal date is information (the case is open), not a gap to fill.
3. Every step prints a before/after count, so the log is evidence rather than claim.
4. The merge asserts its own assumption (`validate="m:1"`) and the row count is
   checked either side, so a fan-out fails loudly instead of quietly tripling totals.
"""

from __future__ import annotations

import pandas as pd

from config import (AGE_BINS, AGE_LABELS, AS_AT, CASES_CLEAN, CASE_TYPE_MAP,
                    CLEANING_LOG, COURTS_CLEAN, OVERDUE_DAYS)
from profile_data import load_raw

AS_AT_TS = pd.Timestamp(AS_AT)


class CleaningLog:
    """Accumulates the decisions taken, for export alongside the data."""

    def __init__(self) -> None:
        self._rows: list[dict] = []

    def add(self, issue: str, rows: int, decision: str, reason: str) -> None:
        self._rows.append(
            {"issue": issue, "rows_affected": rows, "decision": decision, "reason": reason}
        )
        print(f"  [{rows:>5}]  {issue}\n           -> {decision}")

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self._rows)


def standardise_categories(df: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    """Collapse casing, whitespace and abbreviation variants to canonical values.

    An explicit mapping is used rather than fuzzy matching: it is readable,
    reviewable, and it cannot quietly merge two categories that were genuinely
    different.
    """
    for col, mapping in (("case_type", CASE_TYPE_MAP), ("status", {})):
        before = df[col].nunique(dropna=True)
        cleaned = (
            df[col].astype("string").str.strip().str.replace(r"\s+", " ", regex=True).str.title()
        )
        if mapping:
            cleaned = cleaned.replace(mapping)
        df[col] = cleaned
        after = df[col].nunique(dropna=True)
        log.add(
            f"`{col}` had {before} distinct values",
            before - after,
            f"Trimmed, title-cased and mapped variants -> {after} canonical values",
            "Casing, whitespace and abbreviations only; no genuine category was merged",
        )
    return df


def resolve_duplicates(df: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    """Keep one row per case, preferring the more complete record.

    Some duplicate pairs disagree: one row shows the case open, the other
    disposed. That pattern is consistent with a superseded extract, so the row
    carrying a disposal date is treated as the later, more complete one.
    """
    dupes = int(df.duplicated(subset=["case_id"]).sum())
    if dupes:
        df = (
            df.assign(_complete=df["disposed_date"].notna().astype(int))
            .sort_values(["case_id", "_complete"])
            .drop_duplicates(subset=["case_id"], keep="last")
            .drop(columns="_complete")
        )
        log.add(
            "Duplicate case IDs",
            dupes,
            "Kept the more complete record per case ID",
            "Pairs disagreed on status; the row with a disposal date is the later extract",
        )
    return df


def flag_impossible(df: pd.DataFrame, courts: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    """Mark rows that cannot be true, without deleting them."""
    df["quality_flag"] = False
    df["quality_reason"] = pd.NA

    checks = [
        (df["disposed_date"] < df["filed_date"], "disposed before filed"),
        (df["filed_date"] > AS_AT_TS, "filed in the future"),
        (~df["court_id"].isin(courts["court_id"]), "court_id not in lookup"),
    ]
    for mask, reason in checks:
        mask = mask.fillna(False)
        n = int(mask.sum())
        df.loc[mask & ~df["quality_flag"], "quality_reason"] = reason
        df.loc[mask, "quality_flag"] = True
        log.add(
            f"Rows where {reason}",
            n,
            "Flagged and excluded from analysis; retained in the file",
            "Correcting silently would hide a source-system problem",
        )
    return df


def reconcile_duration(df: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    """Compare the source system's duration against one derived from the dates.

    This is the reconciliation control: an independent recomputation of a figure
    the source already supplies. Disagreements are quantified and flagged, never
    overwritten.
    """
    df["reported_days"] = pd.to_numeric(
        df["reported_days"].astype("string").str.strip(), errors="coerce"
    )
    df["waiting_days"] = (df["disposed_date"] - df["filed_date"]).dt.days

    both = df["reported_days"].notna() & df["waiting_days"].notna()
    mismatch = both & (df["reported_days"] != df["waiting_days"])
    df["duration_mismatch"] = mismatch

    log.add(
        "`reported_days` disagrees with the duration calculated from the dates",
        int(mismatch.sum()),
        "Quantified and flagged; the calculated duration is used for analysis",
        "Only findable by checking the source figure against an independent recomputation",
    )
    return df


def derive_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Add the analytical fields the report needs."""
    df["is_open"] = df["disposed_date"].isna()
    df["days_open"] = (AS_AT_TS - df["filed_date"]).dt.days.where(df["is_open"])
    df["filed_month"] = df["filed_date"].dt.to_period("M").astype("string")
    df["filed_quarter"] = df["filed_date"].dt.to_period("Q").astype("string")
    df["disposed_month"] = df["disposed_date"].dt.to_period("M").astype("string")
    df["age_band"] = pd.cut(df["days_open"], bins=AGE_BINS, labels=AGE_LABELS)
    df["overdue"] = df["is_open"] & (df["days_open"] > OVERDUE_DAYS)
    return df


def main() -> pd.DataFrame:
    print("=" * 62)
    print("STAGE 2 — CLEAN")
    print("=" * 62)

    cases, courts = load_raw()
    log = CleaningLog()
    before = len(cases)

    cases = standardise_categories(cases, log)
    cases = resolve_duplicates(cases, log)
    cases = flag_impossible(cases, courts, log)
    cases = reconcile_duration(cases, log)
    cases = derive_fields(cases)

    # --- merge, with the assumption asserted rather than assumed -------------
    rows_before = len(cases)
    merged = cases.merge(courts, on="court_id", how="left", validate="m:1", indicator=True)
    rows_after = len(merged)
    assert rows_before == rows_after, (
        f"Merge changed the row count ({rows_before} -> {rows_after}); "
        "the court lookup key is not unique."
    )
    unmatched = int((merged["_merge"] == "left_only").sum())
    log.add(
        "Cases with no matching court in the lookup",
        unmatched,
        "Left join retained them; already flagged and excluded from court-level analysis",
        "An anti-join finding worth reporting to the data owner, not deleting",
    )
    merged = merged.drop(columns="_merge")

    print(f"\n  rows in  {before:,}   rows out  {len(merged):,}   "
          f"(merge preserved the row count)")

    merged.to_csv(CASES_CLEAN, index=False)
    courts.to_csv(COURTS_CLEAN, index=False)
    log.to_frame().to_csv(CLEANING_LOG, index=False)
    print(f"  written: data/processed/cases_clean.csv, courts_clean.csv, cleaning_log.csv")
    return merged


if __name__ == "__main__":
    main()
