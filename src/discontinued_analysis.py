"""Profile demolition rates by BBR use code and discontinued-code status.

The main ablation reports what happens when discontinued use codes are excluded
(``D1`` versus ``D1-exdisc`` etc.). This script answers a different question:
which use-code groups have implausibly high demolition rates under each
indicator?

Outputs:
    results/demolition_rates_by_use_code.csv
        One row per indicator × last-known use code.
    results/discontinued_rates_by_use_code.csv
        Same table filtered to discontinued last-known use codes.
    results/discontinued_axis_summary.csv
        One row per indicator × discontinued-axis definition.
    results/figures/discontinued_vs_other_rates.{png,pdf}
        Apparent demolition share by discontinued-code status and indicator.
    results/figures/discontinued_code_rate_heatmap.{png,pdf}
        Discontinued use-code rates by indicator.
    results/figures/agriculture_210_replacement_rates.{png,pdf}
        Code 210 compared with agricultural replacement codes 211–219.

Run:
    .venv/bin/python src/discontinued_analysis.py

Use ``--bygning``, ``--sagsniveau`` and ``--bbrsag`` if the cleaned parquet
files are not at the paths configured in ``src/indicators.py``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import polars as pl
import seaborn as sns

import indicators as ind
import plotting

_ROOT = Path(__file__).resolve().parent.parent
RESULTS = _ROOT / "results"
FIGURES = RESULTS / "figures"
AREA_COL = "area_total"


def _last_nonnull(column: str) -> pl.Expr:
    return pl.col(column).drop_nulls().last()


def building_attributes() -> pl.LazyFrame:
    """One row per building with last-known use and discontinued-code flags."""
    use = pl.col("byg021BygningensAnvendelse")
    return (
        pl.scan_parquet(ind.BYGNING_PATH)
        .sort("virkningFra")
        .group_by("id_lokalId")
        .agg(
            _last_nonnull("byg021BygningensAnvendelse").alias("use_code"),
            _last_nonnull("building_use_group").alias("building_use_group"),
            _last_nonnull("byg038SamletBygningsareal").alias(AREA_COL),
            use.is_in(list(ind.DISCONTINUED_CODES)).any().alias("ever_discontinued"),
        )
        .rename({"id_lokalId": "building_id"})
        .with_columns(
            pl.col("use_code")
            .is_in(list(ind.DISCONTINUED_CODES))
            .fill_null(False)
            .alias("last_use_discontinued")
        )
    )


def _rate_columns() -> list[pl.Expr]:
    area = pl.col(AREA_COL)
    demolished = pl.col("demolished")
    valid_demolished_area = demolished & area.is_not_null() & (area >= 0)
    return [
        pl.len().alias("stock_buildings"),
        demolished.sum().alias("demolished_buildings"),
        valid_demolished_area.sum().alias("demolished_buildings_with_area"),
        area.filter(valid_demolished_area).sum().alias("demolished_m2_total"),
        area.filter(valid_demolished_area).median().alias("median_demolished_m2_total"),
    ]


def _with_rates(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        (pl.col("demolished_buildings") / pl.col("stock_buildings") * 100).alias(
            "demolition_rate_pct"
        ),
        pl.when(pl.col("demolished_buildings") > 0)
        .then(
            pl.col("demolished_buildings_with_area")
            / pl.col("demolished_buildings")
            * 100
        )
        .otherwise(None)
        .alias("demolished_area_coverage_pct"),
    )


def rates_by_use_code(indicator: ind.Indicator, attrs: pl.LazyFrame) -> pl.DataFrame:
    """Return one row per last-known use code for one indicator."""
    members = (
        indicator.build()
        .select("building_id")
        .unique()
        .with_columns(pl.lit(True).alias("demolished"))
    )
    joined = attrs.join(members, on="building_id", how="left").with_columns(
        pl.col("demolished").fill_null(False)
    )
    out = (
        joined.group_by("use_code", "building_use_group", "last_use_discontinued")
        .agg(_rate_columns())
        .collect()
        .with_columns(
            pl.lit(indicator.id).alias("indicator"),
            pl.lit(indicator.name).alias("indicator_name"),
        )
    )
    return _with_rates(out).select(
        "indicator",
        "indicator_name",
        "use_code",
        "building_use_group",
        "last_use_discontinued",
        "stock_buildings",
        "demolished_buildings",
        "demolition_rate_pct",
        "demolished_buildings_with_area",
        "demolished_area_coverage_pct",
        "demolished_m2_total",
        "median_demolished_m2_total",
    )


def discontinued_axis_summary(
    indicator: ind.Indicator, attrs: pl.LazyFrame, axis: str
) -> pl.DataFrame:
    """Summarize rates for ever- or last-known discontinued-code flags."""
    members = (
        indicator.build()
        .select("building_id")
        .unique()
        .with_columns(pl.lit(True).alias("demolished"))
    )
    joined = attrs.join(members, on="building_id", how="left").with_columns(
        pl.col("demolished").fill_null(False)
    )
    out = (
        joined.group_by(axis)
        .agg(_rate_columns())
        .collect()
        .with_columns(
            pl.lit(indicator.id).alias("indicator"),
            pl.lit(indicator.name).alias("indicator_name"),
            pl.lit(axis).alias("axis"),
        )
        .rename({axis: "axis_value"})
    )
    return _with_rates(out).select(
        "indicator",
        "indicator_name",
        "axis",
        "axis_value",
        "stock_buildings",
        "demolished_buildings",
        "demolition_rate_pct",
        "demolished_buildings_with_area",
        "demolished_area_coverage_pct",
        "demolished_m2_total",
        "median_demolished_m2_total",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bygning", default=ind.BYGNING_PATH)
    parser.add_argument("--sagsniveau", default=ind.SAGSNIVEAU_PATH)
    parser.add_argument("--bbrsag", default=ind.BBRSAG_PATH)
    parser.add_argument("--output-dir", type=Path, default=RESULTS)
    parser.add_argument(
        "--min-stock",
        type=int,
        default=100,
        help="Minimum denominator for the printed high-rate preview.",
    )
    parser.add_argument("--no-plots", action="store_true")
    return parser.parse_args()


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path.with_suffix(".png"))
    fig.savefig(path.with_suffix(".pdf"))
    plt.close(fig)


def plot_discontinued_vs_other(axis_df: pl.DataFrame, output_dir: Path) -> None:
    """Grouped bars: discontinued-code status versus other buildings."""
    plot_df = (
        axis_df.filter(pl.col("axis") == "last_use_discontinued")
        .with_columns(
            pl.when(pl.col("axis_value"))
            .then(pl.lit("Discontinued code"))
            .otherwise(pl.lit("Other codes"))
            .alias("Use-code status")
        )
        .select("indicator", "Use-code status", "demolition_rate_pct")
        .to_pandas()
    )
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.barplot(
        data=plot_df,
        x="indicator",
        y="demolition_rate_pct",
        hue="Use-code status",
        palette="colorblind",
        ax=ax,
    )
    ax.set_xlabel("Indicator")
    ax.set_ylabel("Buildings selected by indicator (%)")
    ax.set_title("Apparent demolition share by discontinued-code status")
    ax.legend(title=None, frameon=False)
    sns.despine(ax=ax)
    fig.tight_layout()
    _save(fig, output_dir / "discontinued_vs_other_rates")


def plot_discontinued_heatmap(
    discontinued_df: pl.DataFrame, output_dir: Path, min_stock: int
) -> None:
    """Heatmap of discontinued use-code rates across indicators."""
    plot_df = (
        discontinued_df.filter(pl.col("stock_buildings") >= min_stock)
        .with_columns(
            (
                pl.col("use_code").cast(pl.Utf8)
                + " — "
                + pl.col("building_use_group").fill_null("Unknown")
            ).alias("label")
        )
        .pivot(values="demolition_rate_pct", index="label", on="indicator")
        .sort("D1", descending=True)
    )
    labels = plot_df["label"].to_list()
    pdf = plot_df.drop("label").to_pandas()
    pdf.index = labels
    indicator_order = [i.id for i in ind.all_indicators()]
    pdf = pdf[indicator_order]

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        pdf,
        annot=True,
        fmt=".1f",
        cmap="mako_r",
        cbar_kws={"label": "Buildings selected by indicator (%)"},
        ax=ax,
    )
    ax.set_xlabel("Indicator")
    ax.set_ylabel("Last-known discontinued use code")
    ax.set_title("Discontinued use-code demolition shares")
    fig.tight_layout()
    _save(fig, output_dir / "discontinued_code_rate_heatmap")


def plot_agriculture_replacements(
    by_code_df: pl.DataFrame, output_dir: Path, indicators: tuple[str, ...] = ("D1", "D4", "D6", "D7")
) -> None:
    """Grouped bars for discontinued code 210 versus current agricultural codes."""
    codes = list(range(210, 220))
    plot_df = (
        by_code_df.filter(
            pl.col("use_code").is_in(codes) & pl.col("indicator").is_in(indicators)
        )
        .with_columns(pl.col("use_code").cast(pl.Utf8).alias("Use code"))
        .select("indicator", "Use code", "demolition_rate_pct")
        .to_pandas()
    )
    fig, ax = plt.subplots(figsize=(8, 4.8))
    sns.barplot(
        data=plot_df,
        x="Use code",
        y="demolition_rate_pct",
        hue="indicator",
        palette="colorblind",
        ax=ax,
    )
    ax.set_xlabel("Agricultural use code")
    ax.set_ylabel("Buildings selected by indicator (%)")
    ax.set_title("Discontinued agricultural code 210 versus replacement codes")
    ax.legend(title="Indicator", frameon=False, ncol=2)
    sns.despine(ax=ax)
    fig.tight_layout()
    _save(fig, output_dir / "agriculture_210_replacement_rates")


def main() -> None:
    args = parse_args()
    ind.BYGNING_PATH = args.bygning
    ind.SAGSNIVEAU_PATH = args.sagsniveau
    ind.BBRSAG_PATH = args.bbrsag
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print("Rolling up building use-code denominators ...")
    attrs = building_attributes().collect().lazy()

    by_code = []
    axis_summaries = []
    for indicator in ind.all_indicators():
        print(f"  {indicator.id} ...")
        by_code.append(rates_by_use_code(indicator, attrs))
        axis_summaries.append(
            discontinued_axis_summary(indicator, attrs, "ever_discontinued")
        )
        axis_summaries.append(
            discontinued_axis_summary(indicator, attrs, "last_use_discontinued")
        )

    by_code_df = pl.concat(by_code).sort(
        ["indicator", "last_use_discontinued", "demolition_rate_pct"],
        descending=[False, True, True],
        nulls_last=True,
    )
    discontinued_df = by_code_df.filter(pl.col("last_use_discontinued"))
    axis_df = pl.concat(axis_summaries).sort(["indicator", "axis", "axis_value"])

    by_code_path = args.output_dir / "demolition_rates_by_use_code.csv"
    discontinued_path = args.output_dir / "discontinued_rates_by_use_code.csv"
    axis_path = args.output_dir / "discontinued_axis_summary.csv"
    by_code_df.write_csv(by_code_path)
    discontinued_df.write_csv(discontinued_path)
    axis_df.write_csv(axis_path)

    if not args.no_plots:
        figures_dir = args.output_dir / "figures"
        plotting.set_style()
        plot_discontinued_vs_other(axis_df, figures_dir)
        plot_discontinued_heatmap(discontinued_df, figures_dir, args.min_stock)
        plot_agriculture_replacements(by_code_df, figures_dir)

    preview = discontinued_df.filter(pl.col("stock_buildings") >= args.min_stock).sort(
        ["indicator", "demolition_rate_pct"],
        descending=[False, True],
    )
    print(f"\nWrote {by_code_path}")
    print(f"Wrote {discontinued_path}")
    print(f"Wrote {axis_path}")
    if not args.no_plots:
        print(f"Wrote figures under {args.output_dir / 'figures'}")
    print(f"\nHighest discontinued-code rates with stock >= {args.min_stock}:")
    with pl.Config(tbl_cols=-1, tbl_width_chars=160, tbl_rows=30):
        print(
            preview.select(
                "indicator",
                "use_code",
                "building_use_group",
                "stock_buildings",
                "demolished_buildings",
                pl.col("demolition_rate_pct").round(1),
                pl.col("demolished_m2_total").round(0),
            ).head(30)
        )


if __name__ == "__main__":
    main()
