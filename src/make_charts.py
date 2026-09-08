"""Stage 4 — render the figures.

Chart conventions applied throughout:
  * one y-axis per chart, never two scales;
  * a legend whenever two series share a chart, plus direct labels;
  * recessive grid and axes, thin marks, values rounded to the decision;
  * categorical colours taken from validated slots (see docs/methodology.md);
  * every label names a value the chart actually reaches.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from config import (BLUE, CHART_STYLE, COMPLETENESS_FLOOR, FIGURE_DIR, GRID,
                    INK, MUTED, ORANGE, OVERDUE_DAYS, PROCESSED_DIR, SURFACE)

# Two styles. "plain" is matplotlib's own defaults with the chart junk removed -
# it reads as a working notebook. "report" is the more designed version.
# Set CHART_STYLE in src/config.py.
if CHART_STYLE == "report":
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE, "font.size": 10, "text.color": INK,
        "axes.labelcolor": MUTED, "axes.edgecolor": GRID,
        "xtick.color": MUTED, "ytick.color": MUTED,
        "grid.color": GRID, "grid.linewidth": 0.8,
    })
else:
    plt.rcParams.update(plt.rcParamsDefault)
    plt.rcParams.update({"grid.alpha": 0.25})

plt.rcParams.update({
    "figure.dpi": 150,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.axisbelow": True,
})


def _title(ax, title: str, subtitle: str | None = None) -> None:
    ax.set_title(title, loc="left", fontsize=13, color=INK, pad=28 if subtitle else 10)
    if subtitle:
        ax.text(0, 1.015, subtitle, transform=ax.transAxes, fontsize=9,
                color=MUTED, va="bottom")


def _save(fig, name: str) -> None:
    path = FIGURE_DIR / f"{name}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  outputs/figures/{name}.png")


def chart_flow() -> None:
    """Filings against disposals. Two series, one scale, both labelled."""
    d = pd.read_csv(PROCESSED_DIR / "monthly_flow.csv")
    d = d[d["month"].notna()].sort_values("month")
    x = range(len(d))

    fig, ax = plt.subplots(figsize=(9.5, 4.2))
    ax.plot(x, d["filings"], color=BLUE, lw=2, label="Filed")
    ax.plot(x, d["disposals"], color=ORANGE, lw=2, label="Disposed")
    ax.set_xticks(list(x)[::3])
    ax.set_xticklabels(d["month"].iloc[::3], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Cases")
    ax.set_ylim(0, max(d[["filings", "disposals"]].max()) * 1.18)

    last = len(d) - 1
    ax.annotate("Filed", (last, d["filings"].iloc[-1]), xytext=(6, 2),
                textcoords="offset points", color=BLUE, fontsize=9, weight="bold")
    ax.annotate("Disposed", (last, d["disposals"].iloc[-1]), xytext=(6, -10),
                textcoords="offset points", color=ORANGE, fontsize=9, weight="bold")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    _title(ax, "Cases filed and disposed, by month",
           "Either series alone is volume. Together they show whether the system is keeping up.")
    _save(fig, "01_monthly_flow")


def chart_distribution() -> None:
    """The chart that justifies reporting a median rather than a mean."""
    d = pd.read_csv(PROCESSED_DIR.parent / "processed" / "cases_clean.csv")
    w = d.loc[~d["quality_flag"] & d["waiting_days"].notna(), "waiting_days"]
    med, mean = w.median(), w.mean()

    fig, ax = plt.subplots(figsize=(9.5, 4.0))
    ax.hist(w, bins=45, color=BLUE, alpha=0.85, edgecolor="white", linewidth=0.6)
    ax.axvline(med, color=INK, lw=1.6, ls="-")
    ax.axvline(mean, color=ORANGE, lw=1.6, ls="--")
    top = ax.get_ylim()[1]
    ax.text(med, top * 0.96, f"  Median {med:.0f} days", color=INK, fontsize=9, va="top")
    ax.text(mean, top * 0.84, f"  Mean {mean:.0f} days", color=ORANGE, fontsize=9, va="top")
    ax.set_xlabel("Days from filing to disposal")
    ax.set_ylabel("Cases")
    _title(ax, "Distribution of time to disposal",
           "A long right tail: the mean sits above the median, where few actual cases are.")
    _save(fig, "02_distribution")


def chart_region() -> None:
    d = pd.read_csv(PROCESSED_DIR / "summary_by_region.csv").dropna(subset=["median_days"])
    d = d.sort_values("median_days")

    fig, ax = plt.subplots(figsize=(8.0, 3.6))
    bars = ax.barh(d["region"], d["median_days"], color=BLUE, height=0.62)
    ax.bar_label(bars, fmt="%.0f", padding=5, fontsize=9, color=INK)
    ax.set_xlabel("Median days to disposal")
    ax.set_xlim(0, d["median_days"].max() * 1.16)
    ax.grid(axis="y", visible=False)
    spread = d["median_days"].max() - d["median_days"].min()
    _title(ax, "Median time to disposal, by region",
           f"A spread of {spread:.0f} days — roughly {spread/7:.0f} weeks — between the fastest and slowest.")
    _save(fig, "03_region")


def chart_courts() -> None:
    d = pd.read_csv(PROCESSED_DIR / "summary_by_court.csv").dropna(subset=["median_days"])
    d = d.sort_values("median_days")
    national = d["median_days"].median()

    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    bars = ax.barh(d["court_name"], d["median_days"], color=BLUE, height=0.66)
    ax.bar_label(bars, labels=[f"{v:.0f}  (n={int(n)})" for v, n in
                               zip(d["median_days"], d["closed_cases"])],
                 padding=5, fontsize=8, color=INK)
    ax.axvline(national, color=MUTED, lw=1.2, ls="--")
    ax.text(national, len(d) - 0.4, f"  national median {national:.0f}",
            color=MUTED, fontsize=8, va="center")
    ax.set_xlabel("Median days to disposal")
    ax.set_xlim(0, d["median_days"].max() * 1.28)
    ax.grid(axis="y", visible=False)
    _title(ax, "Median time to disposal, by court",
           "Case counts shown so no figure is read without its denominator.")
    _save(fig, "04_courts")


def chart_backlog() -> None:
    d = pd.read_csv(PROCESSED_DIR / "backlog_age_profile.csv")
    piv = d.pivot(index="region", columns="age_band", values="open_cases").fillna(0)
    order = ["0-3 months", "3-12 months", "12+ months"]
    piv = piv[[c for c in order if c in piv.columns]]
    shades = ["#a8c8ee", "#5f9ae0", BLUE]

    fig, ax = plt.subplots(figsize=(8.6, 3.9))
    left = pd.Series(0.0, index=piv.index)
    for i, col in enumerate(piv.columns):
        ax.barh(piv.index, piv[col], left=left, height=0.62,
                color=shades[i], label=col, edgecolor=SURFACE, linewidth=2)
        left += piv[col]
    ax.set_xlabel("Open cases")
    ax.grid(axis="y", visible=False)
    ax.legend(frameon=False, fontsize=9, ncols=3, loc="lower right",
              bbox_to_anchor=(1.0, 1.0), title=None)
    _title(ax, "Open backlog by age, by region",
           "Sequential shading: darker is older. This is the measure that sees the slow cases.")
    _save(fig, "05_backlog")


def chart_censoring() -> None:
    """The finding: apparent improvement that is an artefact of measurement."""
    d = pd.read_csv(PROCESSED_DIR / "disposal_time_by_quarter.csv")
    d = d[d["median_days"].notna()]

    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    regions = sorted(d["region"].unique())
    focus = "Eastern" if "Eastern" in regions else regions[0]

    for region in regions:
        s = d[d["region"] == region].sort_values("filed_quarter")
        is_focus = region == focus
        ax.plot(s["filed_quarter"], s["median_days"],
                color=BLUE if is_focus else "#c9d6e4",
                lw=2.2 if is_focus else 1.4, zorder=3 if is_focus else 1)

    s = d[d["region"] == focus].sort_values("filed_quarter")
    bad = s[~s["complete"]]
    if len(bad):
        ax.axvspan(bad["filed_quarter"].iloc[0], s["filed_quarter"].iloc[-1],
                   color=ORANGE, alpha=0.10, zorder=0)
        mid = bad["filed_quarter"].iloc[len(bad) // 2]
        ax.text(mid, ax.get_ylim()[1] * 0.97,
                f"Incomplete\nfewer than {COMPLETENESS_FLOOR:.0%} of these\nfilings have closed",
                color=ORANGE, fontsize=8.5, ha="center", va="top", linespacing=1.4)

    ax.annotate(focus, (s["filed_quarter"].iloc[0], s["median_days"].iloc[0]),
                xytext=(4, 8), textcoords="offset points",
                color=BLUE, fontsize=9, weight="bold")
    ax.set_ylabel("Median days to disposal")
    ax.set_xlabel("Filing quarter")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
    _title(ax, "Why the recent 'improvement' is not real",
           "Only closed cases can be measured. In recent quarters only the fast ones have closed.")
    _save(fig, "06_censoring")


def main() -> None:
    print("=" * 62)
    print("STAGE 4 — CHARTS")
    print("=" * 62)
    chart_flow()
    chart_distribution()
    chart_region()
    chart_courts()
    chart_backlog()
    chart_censoring()


if __name__ == "__main__":
    main()
