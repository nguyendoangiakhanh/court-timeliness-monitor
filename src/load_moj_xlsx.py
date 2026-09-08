"""Reader for New Zealand Ministry of Justice published data-table workbooks.

The Ministry publishes its justice statistics as multi-sheet Excel workbooks
(see docs/data_sources.md for the exact files and URLs). They are built to be
read by people, not by machines, so every one of them needs the same handling:

  * a title block of one to several rows above the real header;
  * years spread across columns (wide) rather than down rows (long);
  * footnote markers and suppression symbols mixed into numeric columns;
  * merged cells leaving blanks that should carry the value above;
  * trailing note rows below the data.

Rather than hard-coding a layout that will break on the next release, this module
*detects* the structure: it finds the header row, identifies which columns are
years, unpivots to long form, and separates suppression markers from numbers
instead of silently coercing them to null.

Usage
-----
    python src/load_moj_xlsx.py data/raw/<downloaded-file>.xlsx           # inspect
    python src/load_moj_xlsx.py data/raw/<file>.xlsx --sheet "Table 1"    # one sheet
    python src/load_moj_xlsx.py data/raw/<file>.xlsx --tidy-all           # export long CSV
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

# Symbols the Ministry (and most statistical agencies) use in place of a number.
# These are meaning, not missingness: keeping them separate from true nulls is
# the difference between "withheld" and "we do not know".
SUPPRESSION_MARKERS = {
    "S": "suppressed (small count)",
    "C": "confidential",
    "..": "not available",
    ".": "not applicable",
    "-": "nil",
    "*": "see footnote",
    "N/A": "not applicable",
    "n/a": "not applicable",
}

YEAR_RE = re.compile(r"^(19|20)\d{2}(/\d{2,4})?$")


def list_sheets(path: Path) -> list[str]:
    return pd.ExcelFile(path).sheet_names


def find_header_row(path: Path, sheet: str, max_scan: int = 25) -> int:
    """Return the 0-based index of the row that is most likely the real header.

    Heuristic: the first row where at least half the cells are non-empty strings
    and at least two distinct values appear. Title blocks are typically one
    populated cell on an otherwise empty row, which this skips.
    """
    probe = pd.read_excel(path, sheet_name=sheet, header=None, nrows=max_scan)
    for i in range(len(probe)):
        row = probe.iloc[i]
        filled = row.notna().sum()
        if filled >= max(2, probe.shape[1] // 2) and row.dropna().nunique() > 1:
            return i
    return 0


def split_suppression(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Separate a mixed column into numbers and suppression reasons.

    Returns (numeric_values, suppression_reason). A cell that is a known marker
    becomes a reason; a cell that is neither a number nor a known marker becomes
    null with the reason "unparsed", so nothing disappears without a trace.
    """
    text = series.astype("string").str.strip()
    numeric = pd.to_numeric(text.str.replace(",", "", regex=False), errors="coerce")

    reason = pd.Series(pd.NA, index=series.index, dtype="string")
    unresolved = numeric.isna() & text.notna()
    for marker, meaning in SUPPRESSION_MARKERS.items():
        hit = unresolved & (text == marker)
        reason[hit] = meaning
    reason[unresolved & reason.isna()] = "unparsed"
    return numeric, reason


def tidy_sheet(path: Path, sheet: str) -> pd.DataFrame:
    """Read one sheet and return it in long form.

    Wide year columns become rows. Dimension columns are forward-filled to undo
    merged cells. Values are split into a number and a suppression reason.
    """
    header = find_header_row(path, sheet)
    df = pd.read_excel(path, sheet_name=sheet, header=header)
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
    df.columns = [str(c).strip() for c in df.columns]

    year_cols = [c for c in df.columns if YEAR_RE.match(str(c).strip())]
    dim_cols = [c for c in df.columns if c not in year_cols]

    # Drop note and footnote rows before anything else. They are identifiable by
    # having no value in any period column — doing this first stops a footnote
    # being forward-filled into the rows below it.
    if year_cols:
        df = df[df[year_cols].notna().any(axis=1)]

    # Merged cells in the dimension columns read as blanks; carry the value down.
    # Checked by content rather than dtype: pandas 3 infers a string dtype for
    # text columns, so a dtype == object test silently does nothing.
    for c in dim_cols:
        if not pd.api.types.is_numeric_dtype(df[c]):
            df[c] = df[c].ffill()

    if not year_cols:
        df.attrs["shape_note"] = "no year columns detected; returned as-is"
        return df

    long = df.melt(id_vars=dim_cols, value_vars=year_cols,
                   var_name="period", value_name="value_raw")
    long["value"], long["suppression_reason"] = split_suppression(long["value_raw"])
    long["sheet"] = sheet
    long.attrs["shape_note"] = f"unpivoted {len(year_cols)} period columns to long"
    return long


def profile_workbook(path: Path) -> pd.DataFrame:
    """One row per sheet: shape, detected header row, and detected year columns."""
    rows = []
    for sheet in list_sheets(path):
        try:
            header = find_header_row(path, sheet)
            df = pd.read_excel(path, sheet_name=sheet, header=header, nrows=200)
            df.columns = [str(c).strip() for c in df.columns]
            years = [c for c in df.columns if YEAR_RE.match(str(c))]
            rows.append({
                "sheet": sheet,
                "header_row": header,
                "columns": df.shape[1],
                "year_columns": len(years),
                "period_range": f"{years[0]}–{years[-1]}" if years else "",
                "first_columns": ", ".join(list(df.columns)[:4]),
            })
        except Exception as exc:  # a sheet that is pure prose, typically
            rows.append({"sheet": sheet, "header_row": -1, "columns": 0,
                         "year_columns": 0, "period_range": "",
                         "first_columns": f"could not parse: {exc}"})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", type=Path, help="path to a downloaded MOJ .xlsx workbook")
    ap.add_argument("--sheet", help="tidy a single sheet and print the head")
    ap.add_argument("--tidy-all", action="store_true",
                    help="tidy every sheet and write one long CSV")
    ap.add_argument("--out", type=Path, default=Path("data/processed/moj_long.csv"))
    args = ap.parse_args()

    if not args.path.exists():
        raise SystemExit(
            f"\n  Not found: {args.path}\n"
            f"  Download a workbook first — see docs/data_sources.md for the URLs.\n"
        )

    if args.sheet:
        tidy = tidy_sheet(args.path, args.sheet)
        print(f"\n{args.sheet}: {len(tidy):,} rows  ({tidy.attrs.get('shape_note','')})\n")
        print(tidy.head(12).to_string(index=False))
        if "suppression_reason" in tidy:
            counts = tidy["suppression_reason"].value_counts(dropna=True)
            if len(counts):
                print("\nNon-numeric cells:")
                print(counts.to_string())
        return

    if args.tidy_all:
        frames = []
        for sheet in list_sheets(args.path):
            try:
                t = tidy_sheet(args.path, sheet)
                if "period" in t.columns:
                    frames.append(t)
            except Exception as exc:
                print(f"  skipped {sheet}: {exc}")
        if not frames:
            raise SystemExit("  No sheets in wide period format were found.")
        out = pd.concat(frames, ignore_index=True)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(args.out, index=False)
        print(f"\n  {len(out):,} rows from {len(frames)} sheets -> {args.out}")
        supp = out["suppression_reason"].notna().sum()
        print(f"  {supp:,} cells carry a suppression or parse reason rather than a number")
        return

    prof = profile_workbook(args.path)
    print(f"\n{args.path.name} — {len(prof)} sheets\n")
    print(prof.to_string(index=False))
    print("\n  Next: --sheet \"<name>\" to tidy one, or --tidy-all to export them all.\n")


if __name__ == "__main__":
    main()
