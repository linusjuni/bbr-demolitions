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
    results/latest_discontinued_sensitivity.csv
        Full indicator estimates versus estimates after removing buildings whose
        last-known use code is discontinued.
    results/discontinued_code_transition_pairs.csv
        Top same-building transitions from discontinued to current use codes.
    results/discontinued_code_transition_years.csv
        Annual counts of same-building discontinued-to-current recodings.
    results/figures/discontinued_vs_other_rates.{png,pdf}
        Apparent demolition share by discontinued-code status and indicator.
    results/figures/discontinued_code_rate_heatmap.{png,pdf}
        Discontinued use-code rates by indicator.
    results/figures/agriculture_210_replacement_rates.{png,pdf}
        Code 210 compared with agricultural replacement codes 211–219.
    results/figures/latest_discontinued_sensitivity.{png,pdf}
        Percent of each indicator removed by the last-known discontinued-code filter.
    results/figures/discontinued_code_migration.{png,pdf}
        Top old-to-current code transitions and their timing.

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
from matplotlib.ticker import StrMethodFormatter
import polars as pl
import seaborn as sns

import indicators as ind
import plotting

_ROOT = Path(__file__).resolve().parent.parent
RESULTS = _ROOT / "results"
FIGURES = RESULTS / "figures"
AREA_COL = "area_total"
USE_COL = "byg021BygningensAnvendelse"


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


def discontinued_code_transitions() -> pl.DataFrame:
    """First same-building transition from a discontinued to a current use code."""
    return (
        pl.scan_parquet(ind.BYGNING_PATH)
        .select("id_lokalId", "virkningFra", "registreringFra", USE_COL)
        .filter(pl.col(USE_COL).is_not_null())
        .sort(["id_lokalId", "virkningFra", "registreringFra"])
        .with_columns(pl.col(USE_COL).shift(1).over("id_lokalId").alias("old_code"))
        .filter(
            pl.col("old_code").is_in(list(ind.DISCONTINUED_CODES))
            & ~pl.col(USE_COL).is_in(list(ind.DISCONTINUED_CODES))
        )
        .group_by("id_lokalId")
        .agg(
            pl.col("old_code").first().alias("old_code"),
            pl.col(USE_COL).first().alias("new_code"),
            pl.col("virkningFra").first().alias("switch_effect_from"),
            pl.col("registreringFra").first().alias("switch_registration_from"),
        )
        .rename({"id_lokalId": "building_id"})
        .with_columns(
            pl.col("switch_effect_from").dt.year().alias("effect_year"),
            pl.col("switch_registration_from").dt.year().alias("registration_year"),
        )
        .collect()
    )


def transition_pair_summary(transitions: pl.DataFrame) -> pl.DataFrame:
    """Counts by old-code/new-code pair."""
    return (
        transitions.group_by("old_code", "new_code")
        .agg(pl.len().alias("n_buildings"))
        .with_columns(
            (pl.col("n_buildings") / pl.col("n_buildings").sum() * 100).alias(
                "share_pct"
            )
        )
        .sort("n_buildings", descending=True)
    )


def transition_year_summary(transitions: pl.DataFrame) -> pl.DataFrame:
    """Annual counts of discontinued-to-current recodings."""
    summaries = []
    for year_col, year_type in [
        ("effect_year", "effect"),
        ("registration_year", "registration"),
    ]:
        summaries.append(
            transitions.group_by(year_col)
            .agg(pl.len().alias("n_buildings"))
            .rename({year_col: "year"})
            .with_columns(pl.lit(year_type).alias("year_type"))
            .select("year_type", "year", "n_buildings")
        )
    return pl.concat(summaries).sort("year_type", "year")


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


def latest_discontinued_sensitivity(axis_df: pl.DataFrame) -> pl.DataFrame:
    """Full versus last-known-discontinued-excluded estimates by indicator."""
    source = axis_df.filter(pl.col("axis") == "last_use_discontinued")
    out = (
        source.group_by("indicator", "indicator_name")
        .agg(
            pl.col("stock_buildings").sum().alias("full_stock_buildings"),
            pl.col("stock_buildings")
            .filter(~pl.col("axis_value"))
            .sum()
            .alias("kept_stock_buildings"),
            pl.col("stock_buildings")
            .filter(pl.col("axis_value"))
            .sum()
            .alias("removed_latest_discontinued_stock_buildings"),
            pl.col("demolished_buildings").sum().alias("full_demolished_buildings"),
            pl.col("demolished_buildings")
            .filter(~pl.col("axis_value"))
            .sum()
            .alias("kept_demolished_buildings"),
            pl.col("demolished_buildings")
            .filter(pl.col("axis_value"))
            .sum()
            .alias("removed_latest_discontinued_demolished_buildings"),
            pl.col("demolished_buildings_with_area")
            .sum()
            .alias("full_demolished_buildings_with_area"),
            pl.col("demolished_buildings_with_area")
            .filter(~pl.col("axis_value"))
            .sum()
            .alias("kept_demolished_buildings_with_area"),
            pl.col("demolished_buildings_with_area")
            .filter(pl.col("axis_value"))
            .sum()
            .alias("removed_latest_discontinued_buildings_with_area"),
            pl.col("demolished_m2_total").sum().alias("full_m2_total"),
            pl.col("demolished_m2_total")
            .filter(~pl.col("axis_value"))
            .sum()
            .alias("kept_m2_total"),
            pl.col("demolished_m2_total")
            .filter(pl.col("axis_value"))
            .sum()
            .alias("removed_latest_discontinued_m2_total"),
        )
        .with_columns(
            (
                pl.col("removed_latest_discontinued_demolished_buildings")
                / pl.col("full_demolished_buildings")
                * 100
            ).alias("removed_demolished_buildings_pct"),
            (
                pl.col("removed_latest_discontinued_m2_total")
                / pl.col("full_m2_total")
                * 100
            ).alias("removed_m2_pct"),
            (
                pl.col("full_demolished_buildings_with_area")
                / pl.col("full_demolished_buildings")
                * 100
            ).alias("full_area_coverage_pct"),
            (
                pl.col("kept_demolished_buildings_with_area")
                / pl.col("kept_demolished_buildings")
                * 100
            ).alias("kept_area_coverage_pct"),
        )
        .sort("indicator")
    )
    return out.select(
        "indicator",
        "indicator_name",
        "full_stock_buildings",
        "kept_stock_buildings",
        "removed_latest_discontinued_stock_buildings",
        "full_demolished_buildings",
        "kept_demolished_buildings",
        "removed_latest_discontinued_demolished_buildings",
        "removed_demolished_buildings_pct",
        "full_m2_total",
        "kept_m2_total",
        "removed_latest_discontinued_m2_total",
        "removed_m2_pct",
        "full_area_coverage_pct",
        "kept_area_coverage_pct",
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
    by_code_df: pl.DataFrame,
    output_dir: Path,
    indicators: tuple[str, ...] = ("D1", "D4", "D5", "D6"),
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


def plot_latest_discontinued_sensitivity(
    sensitivity_df: pl.DataFrame, output_dir: Path
) -> None:
    """Bars showing how much the latest-discontinued filter removes."""
    plot_df = (
        sensitivity_df.select(
            "indicator", "removed_demolished_buildings_pct", "removed_m2_pct"
        )
        .rename(
            {
                "removed_demolished_buildings_pct": "Demolished buildings",
                "removed_m2_pct": "Demolished total area",
            }
        )
        .to_pandas()
        .melt(
            id_vars="indicator",
            var_name="Outcome",
            value_name="Percent removed",
        )
    )
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.barplot(
        data=plot_df,
        x="indicator",
        y="Percent removed",
        hue="Outcome",
        palette="colorblind",
        ax=ax,
    )
    ax.set_xlabel("Indicator")
    ax.set_ylabel("Removed by latest-discontinued filter (%)")
    ax.set_title("Sensitivity to excluding last-known discontinued codes")
    ax.legend(title=None, frameon=False)
    sns.despine(ax=ax)
    fig.tight_layout()
    _save(fig, output_dir / "latest_discontinued_sensitivity")


def plot_discontinued_code_migration(
    pair_df: pl.DataFrame,
    year_df: pl.DataFrame,
    output_dir: Path,
    top_n: int = 12,
) -> None:
    """Two-panel diagnostic of same-building old-to-current recodings."""
    pairs = (
        pair_df.head(top_n)
        .with_columns(
            (
                pl.col("old_code").cast(pl.Utf8)
                + " -> "
                + pl.col("new_code").cast(pl.Utf8)
            ).alias("Transition")
        )
        .sort("n_buildings")
        .to_pandas()
    )
    years = (
        year_df.filter(
            (pl.col("year_type") == "registration")
            & pl.col("year").is_not_null()
            & (pl.col("year") <= ind.YEAR_MAX)
        )
        .sort("year")
        .to_pandas()
    )

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(11, 4.8),
        gridspec_kw={"width_ratios": [1.35, 1]},
    )
    palette = sns.color_palette("colorblind")
    sns.barplot(
        data=pairs,
        y="Transition",
        x="n_buildings",
        color=palette[0],
        ax=axes[0],
    )
    axes[0].set_xlabel("Buildings")
    axes[0].set_ylabel("Use-code transition")
    axes[0].set_title("Largest discontinued-to-current recodings")
    axes[0].xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))

    sns.barplot(
        data=years,
        x="year",
        y="n_buildings",
        color=palette[1],
        ax=axes[1],
    )
    axes[1].set_xlabel("Registration year")
    axes[1].set_ylabel("Buildings")
    axes[1].set_title("Timing of observed recodings")
    axes[1].yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    axes[1].tick_params(axis="x", rotation=45)

    sns.despine(fig=fig)
    fig.tight_layout()
    _save(fig, output_dir / "discontinued_code_migration")


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
    sensitivity_df = latest_discontinued_sensitivity(axis_df)
    print("Summarizing discontinued-to-current recodings ...")
    transition_df = discontinued_code_transitions()
    transition_pairs_df = transition_pair_summary(transition_df)
    transition_years_df = transition_year_summary(transition_df)

    by_code_path = args.output_dir / "demolition_rates_by_use_code.csv"
    discontinued_path = args.output_dir / "discontinued_rates_by_use_code.csv"
    axis_path = args.output_dir / "discontinued_axis_summary.csv"
    sensitivity_path = args.output_dir / "latest_discontinued_sensitivity.csv"
    transition_pairs_path = args.output_dir / "discontinued_code_transition_pairs.csv"
    transition_years_path = args.output_dir / "discontinued_code_transition_years.csv"
    by_code_df.write_csv(by_code_path)
    discontinued_df.write_csv(discontinued_path)
    axis_df.write_csv(axis_path)
    sensitivity_df.write_csv(sensitivity_path)
    transition_pairs_df.write_csv(transition_pairs_path)
    transition_years_df.write_csv(transition_years_path)

    if not args.no_plots:
        figures_dir = args.output_dir / "figures"
        plotting.set_style()
        plot_discontinued_vs_other(axis_df, figures_dir)
        plot_discontinued_heatmap(discontinued_df, figures_dir, args.min_stock)
        plot_agriculture_replacements(by_code_df, figures_dir)
        plot_latest_discontinued_sensitivity(sensitivity_df, figures_dir)
        plot_discontinued_code_migration(
            transition_pairs_df, transition_years_df, figures_dir
        )

    preview = discontinued_df.filter(pl.col("stock_buildings") >= args.min_stock).sort(
        ["indicator", "demolition_rate_pct"],
        descending=[False, True],
    )
    print(f"\nWrote {by_code_path}")
    print(f"Wrote {discontinued_path}")
    print(f"Wrote {axis_path}")
    print(f"Wrote {sensitivity_path}")
    print(f"Wrote {transition_pairs_path}")
    print(f"Wrote {transition_years_path}")
    if not args.no_plots:
        print(f"Wrote figures under {args.output_dir / 'figures'}")
    print(
        f"\nFound {transition_df.height:,} same-building transitions from "
        "discontinued to current use codes."
    )
    print("Largest discontinued-to-current code transitions:")
    with pl.Config(tbl_cols=-1, tbl_width_chars=120):
        print(
            transition_pairs_df.select(
                "old_code",
                "new_code",
                "n_buildings",
                pl.col("share_pct").round(1),
            ).head(12)
        )
    print("\nLatest-discontinued sensitivity:")
    with pl.Config(tbl_cols=-1, tbl_width_chars=180):
        print(
            sensitivity_df.select(
                "indicator",
                "full_demolished_buildings",
                "kept_demolished_buildings",
                pl.col("removed_demolished_buildings_pct").round(1),
                pl.col("full_m2_total").round(0),
                pl.col("kept_m2_total").round(0),
                pl.col("removed_m2_pct").round(1),
            )
        )
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
