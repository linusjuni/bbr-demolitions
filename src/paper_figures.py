"""Figures for the manuscript (Results), in one fixed style.

Every figure uses the same colour, line style and order for the indicators (palette
decided 2026-11-17, see ``docs/manuscript_review_handover.md``): the seaborn
"colorblind" colours blue, orange, green, pink and sky blue, checked with the dataviz
palette validator on all pairs. D4 and D5 count the same buildings in every year, so
in every dated result they are one series, "D4, D5". Each series also has its own
dash pattern, so the figures still read in greyscale and for colour-blind readers.

Reads the CSVs written by ``ablation.py`` / ``rates.py``; computes nothing itself.
Writes a vector PDF and a 300-dpi PNG per figure to ``results/figures/``.

Run:  ``.venv/bin/python src/paper_figures.py``
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import polars as pl
from matplotlib.ticker import FuncFormatter, MultipleLocator

_ROOT = Path(__file__).resolve().parent.parent
RESULTS = _ROOT / "results"
FIGURES = RESULTS / "figures"

# One entry per series: (label, indicators in the CSVs, colour, dash pattern).
SERIES = [
    ("D1", ["D1"], "#0173b2", "-"),
    ("D2", ["D2"], "#de8f05", (0, (5, 2))),
    ("D3", ["D3"], "#029e73", (0, (1.2, 1.6))),
    ("D4, D5", ["D4", "D5"], "#cc78bc", (0, (6, 2, 1.2, 2))),
    ("D6", ["D6"], "#56b4e9", (0, (2.5, 1.5))),
]
NAMES = {
    "D1": "Historical",
    "D2": "Demolition change",
    "D3": "Historical with demolition change",
    "D4, D5": "Demolition case; Historical with demolition case",
    "D6": "Demolition case, dated by notification",
}
FULL_PERIOD = (2001, 2025)
MAIN_PERIOD = (2018, 2025)

INK = "#222222"
MUTED = "#666666"
GRID = "#e6e6e6"
BAND = "#efefef"
FULL_WIDTH_IN = 7.48  # Elsevier full text width, 190 mm


def set_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 8.5,
            "axes.labelsize": 8.5,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "axes.edgecolor": MUTED,
            "axes.labelcolor": INK,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.6,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "pdf.fonttype": 42,
        }
    )


def _save(fig: plt.Figure, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(FIGURES / f"{name}.{ext}")
    plt.close(fig)


def _series(df: pl.DataFrame, members: list[str], value: str) -> pl.DataFrame:
    """One indicator's yearly values (the first member; D4 and D5 are identical)."""
    return df.filter(pl.col("variant") == members[0]).sort("year").select("year", value)


def fig_annual() -> None:
    """Fig. 1: buildings (a) and floor area (b) per year, full period, all indicators."""
    lo, hi = FULL_PERIOD
    df = pl.read_csv(RESULTS / "annual.csv").filter(pl.col("year").is_between(lo, hi))
    # D4 and D5 must be identical in every year for the shared series to be honest.
    d4 = df.filter(pl.col("variant") == "D4").sort("year")
    d5 = df.filter(pl.col("variant") == "D5").sort("year")
    assert d4["n_buildings"].to_list() == d5["n_buildings"].to_list()
    assert d4["m2_total"].to_list() == d5["m2_total"].to_list()

    fig, axes = plt.subplots(2, 1, figsize=(FULL_WIDTH_IN, 5.2), sharex=True)
    panels = [
        ("n_buildings", 1e3, "Demolished buildings\n(thousands)", 5),
        ("m2_total", 1e6, "Demolished floor area\n(million m²)", 0.5),
    ]
    for ax, (value, scale, ylabel, step), letter in zip(axes, panels, "ab"):
        ax.axvspan(MAIN_PERIOD[0] - 0.5, MAIN_PERIOD[1] + 0.5, color=BAND, lw=0, zorder=0)
        ax.yaxis.grid(True, color=GRID, lw=0.6, zorder=0)
        ax.set_axisbelow(True)
        for label, members, colour, dash in SERIES:
            s = _series(df, members, value)
            ax.plot(s["year"], s[value] / scale, color=colour, ls=dash, lw=1.6,
                    label=f"{label}  {NAMES[label]}", zorder=3,
                    solid_capstyle="round", dash_capstyle="round")
        ax.set_ylabel(ylabel)
        ax.set_ylim(bottom=0)
        ax.yaxis.set_major_locator(MultipleLocator(step))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
        ax.text(-0.075, 1.0, f"({letter})", transform=ax.transAxes, ha="left",
                va="top", fontsize=9, fontweight="bold", color=INK)
    for ax in axes:
        ax.text((MAIN_PERIOD[0] + MAIN_PERIOD[1]) / 2, 1.01,
                "Main comparison period", transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=7.5, color=MUTED, clip_on=False)
    axes[1].set_xlim(lo - 0.5, hi + 0.5)
    axes[1].set_xticks([2001, 2005, 2010, 2015, 2018, 2020, 2025])
    axes[1].xaxis.set_minor_locator(MultipleLocator(1))
    axes[1].set_xlabel("Year")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False,
               bbox_to_anchor=(0.5, 1.09), handlelength=3.2, columnspacing=2.0)
    fig.tight_layout(h_pad=2.0)
    _save(fig, "fig_annual")

# Ordinal / sequential blue ramp (dataviz reference palette, light -> dark).
BLUES = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281"]
MARKERS = {"D1": "o", "D2": "s", "D3": "^", "D4, D5": "D", "D6": "v"}


def fig_overlap() -> None:
    """Fig. 2: (a) Jaccard index per pair, (b) shared buildings per indicator, 2018-2025."""
    from matplotlib.colors import LinearSegmentedColormap

    jac = pl.read_csv(RESULTS / "overlap_2018_2025.csv")
    sh = pl.read_csv(RESULTS / "overlap_shared_2018_2025.csv")
    ids = ["D1", "D2", "D3", "D4", "D5", "D6"]
    j = {(r["a"], r["b"]): r["jaccard"] for r in jac.iter_rows(named=True)}

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(FULL_WIDTH_IN, 3.0), gridspec_kw={"width_ratios": [1, 1.35]}
    )
    cmap = LinearSegmentedColormap.from_list("blues", BLUES)
    rows, cols = ids[1:], ids[:-1]
    for r, a in enumerate(rows):
        for c, b in enumerate(cols):
            if c > r:
                continue
            v = j[(a, b)]
            ax1.add_patch(plt.Rectangle((c, r), 0.94, 0.94, color=cmap(v), lw=0))
            ax1.text(c + 0.47, r + 0.47, f"{v:.2f}", ha="center", va="center",
                     fontsize=7.5, color="white" if v > 0.6 else INK)
    ax1.set_xlim(-0.03, len(cols))
    ax1.set_ylim(len(rows), -0.03)
    ax1.set_xticks([c + 0.47 for c in range(len(cols))], cols)
    ax1.set_yticks([r + 0.47 for r in range(len(rows))], rows)
    ax1.tick_params(length=0)
    ax1.xaxis.tick_top()
    for sp in ax1.spines.values():
        sp.set_visible(False)
    ax1.set_aspect("equal")

    labels = ["D1", "D2", "D3", "D4, D5", "D6"]
    parts = [("none", [0], BLUES[6]), ("some", [1, 2, 3], BLUES[3]), ("all", [4], BLUES[1])]
    for y, lab in enumerate(labels):
        d = sh.filter(pl.col("series") == lab)
        left = 0.0
        for name, ns, colour in parts:
            w = d.filter(pl.col("n_others").is_in(ns))["share_pct"].sum()
            ax2.barh(y, w, left=left, color=colour, height=0.62, lw=0)
            if w >= 6:
                ax2.text(left + w / 2, y, f"{w:.0f} %", ha="center", va="center",
                         fontsize=7.5, color="white" if name != "all" else INK)
            if w > 0:
                left += w + 0.6  # small surface gap between segments
    ax2.set_yticks(range(len(labels)), labels)
    ax2.set_ylim(len(labels) - 0.5, -0.5)
    ax2.set_xlim(0, 101.8)
    ax2.set_xticks([0, 25, 50, 75, 100])
    ax2.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g} %"))
    ax2.set_xlabel("Share of the indicator's buildings")
    ax2.tick_params(axis="y", length=0)
    ax2.spines["left"].set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in parts]
    ax2.legend(handles, ["Counted by none of the others", "By some", "By all"],
               loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=False,
               handlelength=1.0, columnspacing=1.2)
    for ax, letter in ((ax1, "a"), (ax2, "b")):
        ax.text(-0.12, 1.12, f"({letter})", transform=ax.transAxes, ha="left", va="bottom",
                fontsize=9, fontweight="bold", color=INK)
    fig.tight_layout(w_pad=3.0)
    _save(fig, "fig_overlap")


def fig_composition() -> None:
    """Fig. 3: mean buildings and floor area per year by use group and construction period.

    Use groups have no order: dot plots, groups sorted by the mean number of buildings
    across the series ("No use code" last). Construction periods are ordered ten-year
    periods: connected dots (lines with markers) in the Fig. 1 styles, with the
    "Missing or placeholder" group as a separate point after a gap.
    """
    comp = pl.read_csv(RESULTS / "composition_2018_2025.csv")
    for axis in ("use", "period"):
        a = comp.filter((pl.col("indicator") == "D4") & (pl.col("axis") == axis))
        b = comp.filter((pl.col("indicator") == "D5") & (pl.col("axis") == axis))
        assert a["buildings_per_year"].to_list() == b["buildings_per_year"].to_list()
    first = {label: members[0] for label, members, *_ in SERIES}

    fig, axes = plt.subplots(2, 2, figsize=(FULL_WIDTH_IN, 6.6),
                             gridspec_kw={"height_ratios": [1, 1.05]})
    values = [("buildings_per_year", 1e3, "Demolished buildings per year (thousands)"),
              ("m2_per_year", 1e6, "Demolished floor area per year (million m²)")]

    # (a, b) building use: dot plots, same group order in both panels
    use = comp.filter(pl.col("axis") == "use")
    order = (
        use.filter(pl.col("indicator").is_in(list(first.values())))
        .group_by("group").agg(pl.col("buildings_per_year").mean())
        .sort("buildings_per_year", descending=True)["group"].to_list()
    )
    order = [g for g in order if g != "No use code"] + ["No use code"]
    offsets = {lab: (k - 2) * 0.13 for k, (lab, *_r) in enumerate(SERIES)}
    for ax, (value, scale, xlabel) in zip(axes[0], values):
        for g in range(len(order)):
            if g % 2 == 0:
                ax.axhspan(g - 0.5, g + 0.5, color="#f6f6f6", lw=0, zorder=0)
        for label, members, colour, _dash in SERIES:
            d = use.filter(pl.col("indicator") == members[0])
            v = dict(zip(d["group"], d[value]))
            ax.scatter([v[g] / scale for g in order],
                       [k + offsets[label] for k in range(len(order))],
                       s=26, color=colour, marker=MARKERS[label], edgecolor="white",
                       linewidth=0.5, zorder=3, label=f"{label}  {NAMES[label]}")
        ax.set_yticks(range(len(order)), order)
        ax.set_ylim(len(order) - 0.5, -0.5)
        ax.set_xlim(left=0)
        ax.xaxis.grid(True, color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        ax.tick_params(axis="y", length=0)
        ax.set_xlabel(xlabel)
    axes[0, 1].set_yticklabels([])
    axes[0, 0].set_ylabel("Building use")  # (b) shares the rows of (a)

    # (c, d) construction period: connected dots over the ordered periods
    per = comp.filter(pl.col("axis") == "period")
    groups = per.filter(pl.col("indicator") == "D1")["group"].to_list()
    ordered = [g for g in groups if g != "Missing or placeholder"]
    x = list(range(len(ordered)))
    x_missing = len(ordered) + 0.8
    ticks = ["Before 1900"] + [g.split("\u2013")[0] + "s" for g in ordered[1:-1]] + ["2020 onwards"]
    for ax, (value, scale, ylabel) in zip(axes[1], values):
        ax.yaxis.grid(True, color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        for label, members, colour, dash in SERIES:
            d = per.filter(pl.col("indicator") == members[0])
            v = dict(zip(d["group"], d[value]))
            ax.plot(x, [v[g] / scale for g in ordered], color=colour, ls=dash, lw=1.4,
                    marker=MARKERS[label], ms=3.6, mec="white", mew=0.4, zorder=3,
                    dash_capstyle="round")
            ax.plot([x_missing], [v["Missing or placeholder"] / scale], color=colour,
                    marker=MARKERS[label], ms=4.2, mec="white", mew=0.4, ls="none",
                    zorder=3)
        ax.axvline(len(ordered) + 0.1, color=GRID, lw=0.8)
        ax.set_xticks(x + [x_missing], ticks + ["Missing or placeholder"],
                      rotation=45, ha="right", rotation_mode="anchor", fontsize=7)
        ax.set_xlim(-0.6, x_missing + 0.7)
        ax.set_ylim(bottom=0)
        ax.set_ylabel(ylabel)
        ax.set_xlabel("Construction period")
    for ax, letter in zip(axes.flat, "abcd"):
        ax.text(0.0, 1.02, f"({letter})", transform=ax.transAxes, ha="left",
                va="bottom", fontsize=9, fontweight="bold", color=INK)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    line_handles = [
        plt.Line2D([], [], color=c, ls=dsh, lw=1.4, marker=MARKERS[lab], ms=4,
                   mec="white", mew=0.4)
        for lab, _m, c, dsh in SERIES
    ]
    fig.legend(line_handles, labels, loc="upper center", ncol=2, frameon=False,
               bbox_to_anchor=(0.5, 1.07), handlelength=3.2, columnspacing=2.0)
    fig.tight_layout(h_pad=2.2, w_pad=1.5)
    _save(fig, "fig_composition")


def main() -> None:
    set_style()
    fig_annual()
    fig_overlap()
    fig_composition()
    print(f"Wrote figures to {FIGURES}")


if __name__ == "__main__":
    main()
