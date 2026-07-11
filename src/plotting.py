"""Figures for the demolition-indicator ablation — importable, seaborn-based.

Kept separate from ``ablation.py`` so the plots can be regenerated (or restyled)
without recomputing the 14-variant sweep: the driver hands each function a ready
DataFrame. Every axis label, title and legend is English-only.

Style follows publication-figure guidance (seaborn ``colorblind`` palette + ``paper``
context, redundant encoding via distinct markers *and* line styles so series stay
separable in greyscale/for colour-blind readers, and 300-DPI PNG **plus** a vector
PDF for each figure). Set once in ``set_style``.

Sources for the conventions applied here:
- seaborn, "Choosing color palettes" — https://seaborn.pydata.org/tutorial/color_palettes.html
- "Best practices for colour blind friendly publications" (PoS) — https://pos.sissa.it/guidelines.pdf
- "Creating Publication-Ready Scientific Figures" —
  https://haibol2016.github.io/data-visualization/scientific-communication/bioinformatics/2026/01/02/012-publication-ready-figures-guide.html
"""

from __future__ import annotations

from itertools import cycle
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import polars as pl
import seaborn as sns

# Redundant encoding: every series uses the same round marker ("o") but cycles line
# styles alongside colour, so a reader who cannot separate hues (greyscale print, colour
# blindness) can still tell series apart via the dash pattern.
_MARKER = "o"
_LINESTYLES = ["-", "--", "-.", ":"]

DPI = 300


def set_style() -> None:
    """Apply the shared publication style. Call once before plotting."""
    sns.set_theme(context="paper", style="ticks", palette="colorblind")
    plt.rcParams.update(
        {
            "figure.dpi": DPI,
            "savefig.dpi": DPI,
            "savefig.bbox": "tight",
            "axes.titleweight": "bold",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def _save(fig: plt.Figure, path: Path) -> None:
    """Write PNG (raster, 300 DPI) and a sibling PDF (vector) for the same figure."""
    fig.savefig(path.with_suffix(".png"))
    fig.savefig(path.with_suffix(".pdf"))
    plt.close(fig)


def annual_lines(
    annual_df: pl.DataFrame,
    value: str,
    ylabel: str,
    title: str,
    path: Path,
    series: list[str],
) -> None:
    """Line-per-indicator time series (one line per ``variant`` in ``series``).

    ``value`` is the column to plot (e.g. ``n_buildings`` or ``m2_etage``); ``series``
    is the ordered list of variant labels to draw.
    """
    fig, ax = plt.subplots(figsize=(7, 4.5))
    palette = sns.color_palette("colorblind", n_colors=len(series))
    styles = cycle(_LINESTYLES)
    for label, colour in zip(series, palette):
        sub = annual_df.filter(pl.col("variant") == label).sort("year")
        if sub.height:
            ax.plot(
                sub["year"],
                sub[value],
                color=colour,
                marker=_MARKER,
                markersize=4,
                linestyle=next(styles),
                linewidth=1.4,
                label=label,
            )
    ax.set_xlabel("Year")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(title="Indicator", ncol=2, frameon=False, fontsize=8)
    sns.despine(ax=ax)
    fig.tight_layout()
    _save(fig, path)


def area_definition_bars(
    summary_df: pl.DataFrame,
    area_defs: list[str],
    title: str,
    path: Path,
    series: list[str],
) -> None:
    """Grouped bars: total demolished area per indicator under each area definition.

    Long-form via seaborn so the legend and colours come from the theme. Values are
    converted to millions of m² for readability.
    """
    records = []
    for label in series:
        row = summary_df.filter(pl.col("variant") == label)
        if not row.height:
            continue
        for a in area_defs:
            records.append(
                {
                    "Indicator": label,
                    "Area definition": a,
                    "area_mln_m2": row[f"m2_{a}"][0] / 1e6,
                }
            )
    long = pl.DataFrame(records).to_pandas()

    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.barplot(
        data=long,
        x="Indicator",
        y="area_mln_m2",
        hue="Area definition",
        palette="colorblind",
        ax=ax,
    )
    ax.set_ylabel("Total demolished area (million m²)")
    ax.set_xlabel("Indicator")
    ax.set_title(title)
    ax.legend(title="Area definition", frameon=False, fontsize=8)
    sns.despine(ax=ax)
    fig.tight_layout()
    _save(fig, path)


def overlap_heatmap(overlap_df: pl.DataFrame, title: str, path: Path) -> None:
    """Jaccard-overlap heatmap among the base indicators."""
    mat = (
        overlap_df.pivot(values="jaccard", index="a", on="b")
        .sort("a")
        .to_pandas()
        .set_index("a")
    )
    mat = mat[mat.index.tolist()]  # order columns to match rows

    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(
        mat,
        annot=True,
        fmt=".2f",
        cmap="cividis",  # perceptually uniform, colour-blind safe
        vmin=0,
        vmax=1,
        square=True,
        cbar_kws={"label": "Jaccard overlap"},
        ax=ax,
    )
    ax.set_xlabel("Indicator")
    ax.set_ylabel("Indicator")
    ax.set_title(title)
    fig.tight_layout()
    _save(fig, path)
