"""Stage 3 — build the reporting tables.

The one analytical judgement worth reading closely is `disposal_time_by_quarter`.
Median time-to-disposal can only be measured on cases that have closed. For
recently filed cases only the fast ones have closed, so the most recent quarters
are made up almost entirely of quick cases and the median collapses — the series
appears to improve when nothing has improved. The function measures how complete
each quarter is and marks the unreliable ones rather than reporting them.
"""

from __future__ import annotations

import pandas as pd

from config import (AGE_LABELS, CASES_CLEAN, COMPLETENESS_FLOOR, OVERDUE_DAYS,
                    PROCESSED_DIR, SUPPRESSION_THRESHOLD)


def load_clean() -> pd.DataFrame:
    df = pd.read_csv(CASES_CLEAN, parse_dates=["filed_date", "disposed_date"],
                     dtype={"case_id": "string", "court_id": "string"})
    return df


def analysable(df: pd.DataFrame) -> pd.DataFrame:
    """Rows usable for court- and region-level reporting."""
    return df[~df["quality_flag"]].copy()


def suppress(series: pd.Series, n: pd.Series) -> pd.Series:
    """Blank any figure resting on fewer than the threshold number of cases.

    In a small jurisdiction a cell of two or three can identify a person. Real
    suppression is harder than this — if row totals are published too, a reader
    can sometimes recover a suppressed cell by subtraction — but the principle
    belongs in the pipeline rather than in a caveat nobody reads.
    """
    return series.where(n >= SUPPRESSION_THRESHOLD)


def summary_by_region(df: pd.DataFrame) -> pd.DataFrame:
    closed = df[df["disposed_date"].notna()]
    g = closed.groupby("region").agg(
        closed_cases=("case_id", "nunique"),
        median_days=("waiting_days", "median"),
        mean_days=("waiting_days", "mean"),
        p75_days=("waiting_days", lambda s: s.quantile(0.75)),
    )
    backlog = df[df["is_open"]].groupby("region").agg(
        open_cases=("case_id", "nunique"),
        overdue_cases=("overdue", "sum"),
    )
    out = g.join(backlog, how="outer").reset_index()
    out["overdue_pct"] = (out["overdue_cases"] / out["open_cases"] * 100).round(1)
    out["median_days"] = suppress(out["median_days"], out["closed_cases"]).round(0)
    out["mean_days"] = suppress(out["mean_days"], out["closed_cases"]).round(0)
    return out.sort_values("median_days", ascending=False)


def summary_by_court(df: pd.DataFrame) -> pd.DataFrame:
    closed = df[df["disposed_date"].notna()]
    g = closed.groupby(["court_name", "region", "court_type"]).agg(
        closed_cases=("case_id", "nunique"),
        median_days=("waiting_days", "median"),
    )
    backlog = df[df["is_open"]].groupby(["court_name", "region", "court_type"]).agg(
        open_cases=("case_id", "nunique"),
        overdue_cases=("overdue", "sum"),
    )
    out = g.join(backlog, how="outer").reset_index()
    out["overdue_pct"] = (out["overdue_cases"] / out["open_cases"] * 100).round(1)
    out["median_days"] = suppress(out["median_days"], out["closed_cases"]).round(0)
    return out.sort_values("median_days", ascending=False)


def monthly_flow(df: pd.DataFrame) -> pd.DataFrame:
    """Filings and disposals per month.

    Reported together on purpose: either series alone is a volume figure, but
    the pair answers the question people actually have, which is whether the
    system is keeping up with what arrives.
    """
    filed = df.groupby("filed_month")["case_id"].nunique().rename("filings")
    disposed = (
        df[df["disposed_date"].notna()]
        .groupby("disposed_month")["case_id"].nunique().rename("disposals")
    )
    out = pd.concat([filed, disposed], axis=1).fillna(0).astype(int)
    out.index.name = "month"
    out = out.reset_index().sort_values("month")
    out["net_change"] = out["filings"] - out["disposals"]
    return out


def backlog_age_profile(df: pd.DataFrame) -> pd.DataFrame:
    open_cases = df[df["is_open"]]
    out = (
        open_cases.groupby(["region", "age_band"], observed=False)["case_id"]
        .nunique().rename("open_cases").reset_index()
    )
    out["open_cases"] = out["open_cases"].where(out["open_cases"] >= SUPPRESSION_THRESHOLD)
    out["age_band"] = pd.Categorical(out["age_band"], categories=AGE_LABELS, ordered=True)
    return out.sort_values(["region", "age_band"])


def disposal_time_by_quarter(df: pd.DataFrame) -> pd.DataFrame:
    """Median time to disposal by filing quarter, with a completeness flag.

    `closure_rate` is the share of that quarter's filings that have closed. Where
    it falls below the floor, the median is computed from a biased subset — the
    fast cases — and is marked incomplete rather than reported as an improvement.
    """
    g = df.groupby(["filed_quarter", "region"]).agg(
        filed=("case_id", "nunique"),
        closed=("disposed_date", "count"),
        median_days=("waiting_days", "median"),
    ).reset_index()
    g["closure_rate"] = (g["closed"] / g["filed"]).round(3)
    g["complete"] = g["closure_rate"] >= COMPLETENESS_FLOOR
    g["median_days"] = suppress(g["median_days"], g["closed"]).round(0)
    return g.sort_values(["region", "filed_quarter"])


def headline(df: pd.DataFrame) -> dict:
    closed = df[df["disposed_date"].notna()]
    open_cases = df[df["is_open"]]
    return {
        "total_cases": int(df["case_id"].nunique()),
        "closed_cases": int(closed["case_id"].nunique()),
        "open_cases": int(open_cases["case_id"].nunique()),
        "median_days_national": float(closed["waiting_days"].median()),
        "mean_days_national": float(closed["waiting_days"].mean()),
        "overdue_cases": int(open_cases["overdue"].sum()),
        "overdue_pct": float(open_cases["overdue"].mean() * 100),
        "excluded_rows": int(df["quality_flag"].sum()) if "quality_flag" in df else 0,
    }


def main() -> dict:
    print("=" * 62)
    print("STAGE 3 — ANALYSE")
    print("=" * 62)

    full = load_clean()
    df = analysable(full)

    tables = {
        "summary_by_region": summary_by_region(df),
        "summary_by_court": summary_by_court(df),
        "monthly_flow": monthly_flow(df),
        "backlog_age_profile": backlog_age_profile(df),
        "disposal_time_by_quarter": disposal_time_by_quarter(df),
    }
    for name, tbl in tables.items():
        path = PROCESSED_DIR / f"{name}.csv"
        tbl.to_csv(path, index=False)
        print(f"  {name:<28} {len(tbl):>4} rows  ->  data/processed/{name}.csv")

    h = headline(full)
    print()
    print(f"  national median days to disposal   {h['median_days_national']:.0f}")
    print(f"  national mean days to disposal     {h['mean_days_national']:.0f}"
          f"   (mean > median: right-skewed)")
    print(f"  open cases                         {h['open_cases']:,}")
    print(f"  open longer than {OVERDUE_DAYS} days        {h['overdue_cases']:,}"
          f"  ({h['overdue_pct']:.1f}%)")
    print(f"  rows excluded as unusable          {h['excluded_rows']}")

    incomplete = tables["disposal_time_by_quarter"].query("not complete")
    print(f"\n  quarters flagged incomplete        {len(incomplete)}"
          f"   (closure rate < {COMPLETENESS_FLOOR:.0%})")
    return {"tables": tables, "headline": h}


if __name__ == "__main__":
    main()
