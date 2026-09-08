#!/usr/bin/env python3
"""Court Timeliness Monitor — run the whole pipeline.

    python run_pipeline.py

Runs profile -> clean -> analyse -> charts in order and writes every output.
The pipeline is deterministic: the same inputs always produce the same outputs,
including the reporting date, which is pinned in src/config.py rather than taken
from today's date.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import analyse
import clean_data
import make_charts
import make_report
import profile_data


def main() -> None:
    print("\nCourt Timeliness Monitor — synthetic data, for practice only\n")
    profile_data.main()
    print()
    clean_data.main()
    print()
    analyse.main()
    print()
    make_charts.main()
    print()
    make_report.main()
    print("\n" + "=" * 62)
    print("Done. See outputs/ and data/processed/.")
    print("=" * 62 + "\n")


if __name__ == "__main__":
    main()
