"""Shared configuration for the Court Timeliness Monitor pipeline.

All paths are resolved relative to the project root so the pipeline runs
identically from any working directory.
"""

from pathlib import Path

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"
DOCS_DIR = ROOT / "docs"

CASES_RAW = RAW_DIR / "cases_raw.csv"
COURTS_RAW = RAW_DIR / "courts.csv"

CASES_CLEAN = PROCESSED_DIR / "cases_clean.csv"
COURTS_CLEAN = PROCESSED_DIR / "courts_clean.csv"
CLEANING_LOG = PROCESSED_DIR / "cleaning_log.csv"

for _d in (PROCESSED_DIR, OUTPUT_DIR, FIGURE_DIR, DOCS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- analysis parameters
# The reporting "as at" date. Fixed rather than datetime.today() so the pipeline
# is reproducible: re-running it next month must not silently change the results.
AS_AT = "2026-09-01"

# Date format in the source extract (day-first, as used in New Zealand).
DATE_FORMAT = "%d/%m/%Y"

# Values that mean "missing" in the source extract.
NA_VALUES = ["", "NA", "N/A", "-", "Unknown", "unknown"]

# A case is "overdue" once it has been open longer than this.
# Chosen for this exercise; in a real setting this threshold is owned by the business.
OVERDUE_DAYS = 365

# Age bands for the open backlog, in days.
AGE_BINS = [-1, 90, 365, 10**6]
AGE_LABELS = ["0-3 months", "3-12 months", "12+ months"]

# Minimum cell size before a count may be published. Small counts can identify
# individuals in a small jurisdiction. Real thresholds are set by the publishing agency.
SUPPRESSION_THRESHOLD = 5

# Disposal-time measures are unreliable for recently filed cases: only the fast
# cases have closed yet, so recent periods look artificially good. Quarters whose
# closure rate falls below this are flagged as incomplete rather than reported.
COMPLETENESS_FLOOR = 0.80

# Canonical category values, and the variants seen in the source extract.
CASE_TYPE_MAP = {
    "Fam": "Family",
    "Family Court": "Family",
    "Yth": "Youth",
    "Crim": "Criminal",
}

# ---------------------------------------------------------------- chart palette
# Validated categorical slots 1 and 2 (see docs/methodology.md).
BLUE = "#2a78d6"
ORANGE = "#eb6834"
INK = "#1a1a19"
MUTED = "#6b6b66"
GRID = "#e4e4e0"
SURFACE = "#fcfcfb"
