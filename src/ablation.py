"""Run the demolition-indicator ablation.

Each indicator in ``indicators.py`` returns only ``building_id`` + ``year`` — the
*membership* of the demolished set under that definition. This driver attaches the
outcome measures the article reports (``docs/indicators.md`` "Ablation scope") and
sweeps the full 14-cell variant grid (``all_variants``):

    - counts        — robust anchor (footprint area is ~complete, so counts are trustworthy)
    - demolished m² — under THREE area definitions, side by side, because the divergence
                      between them IS a result (secondary question 5), not a nuisance:
                        footprint  byg041BebyggetAreal          (~complete)
                        total      byg038SamletBygningsareal    (~54% null on demolished)
                        etage      byg039Bolig + byg040Erhverv  (BUILD basis; sparser still)
    - coverage %    — the fraction of demolished buildings with a non-null area, per column.
                      The papers drop missing-area buildings (Andersen 2023, explicit) and
                      don't report coverage; on THIS extract "drop missing" discards >50%,
                      so we sum available area with NO imputation and report coverage openly.

Per-building attributes (area, use-code, region, construction year) are rolled up from
``bygning.parquet`` here — this is aggregation plumbing, not a demolition decision, so it
lives in the driver, never in an indicator (the indicators stay pure per the article's
"no opaque contract" principle).

Outputs (written under ``results/``):
    ablation_summary.csv   one row per variant: counts, total/median m² + coverage per area def
    annual.csv             variant × year: count and m² per area def
    by_region.csv          variant × region: count and floor-area m²
    overlap.csv            pairwise intersection + Jaccard among the 7 base indicators
    figures/*.png + *.pdf  annual_counts, annual_area_etage,
                           area_definition_sensitivity, overlap_heatmap
                           (rendered by src/plotting.py — seaborn, English labels)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl

import indicators as ind
import plotting

_ROOT = Path(__file__).resolve().parent.parent
RESULTS = _ROOT / "results"
FIGURES = RESULTS / "figures"

# The three area definitions swept side by side. `etage` (BUILD's bolig+erhverv basis)
# is derived below; the other two are raw columns. Order = increasing missingness.
AREA_DEFS = ["footprint", "total", "etage"]


# --- Per-building attribute rollup ------------------------------------------
# One row per building. Area/use/region taken as the LAST KNOWN non-null value over the
# building's full temporal history (its most recent registered state before exit). We
# verified max-over-history barely differs from the value at the status-10 row for the
# total-area column (+5.6k of 247k nulls recovered), so the nulls are genuine missingness,
# not blanked-on-exit — hence honest coverage reporting rather than backfill.


def build_attributes() -> pl.LazyFrame:
    """LazyFrame[building_id, area_footprint, area_total, area_etage, use_code,
    region_name, construction_year] — one row per building."""
    lf = pl.scan_parquet(ind.BYGNING_PATH).sort("virkningFra")

    def last_nonnull(col: str) -> pl.Expr:
        return pl.col(col).drop_nulls().last()

    rolled = lf.group_by("id_lokalId").agg(
        last_nonnull("byg041BebyggetAreal").alias("area_footprint"),
        last_nonnull("byg038SamletBygningsareal").alias("area_total"),
        last_nonnull("byg039BygningensSamledeBoligAreal").alias("_bolig"),
        last_nonnull("byg040BygningensSamledeErhvervsAreal").alias("_erhverv"),
        last_nonnull("byg021BygningensAnvendelse").alias("use_code"),
        last_nonnull("region_name").alias("region_name"),
        last_nonnull("byg026Opførelsesår").alias("construction_year"),
    )
    return rolled.select(
        pl.col("id_lokalId").alias("building_id"),
        "area_footprint",
        "area_total",
        # etageareal = bolig + erhverv (BUILD). Null only when BOTH are null (no info);
        # if one is present the other counts as 0 — matches BUILD's bolig+erhverv sum.
        pl.when(pl.col("_bolig").is_null() & pl.col("_erhverv").is_null())
        .then(None)
        .otherwise(pl.col("_bolig").fill_null(0) + pl.col("_erhverv").fill_null(0))
        .alias("area_etage"),
        "use_code",
        "region_name",
        "construction_year",
    )


# --- Per-variant statistics -------------------------------------------------


def summarise(label: str, demolished: pl.LazyFrame, attrs: pl.LazyFrame) -> pl.DataFrame:
    """One-row summary for a variant: count + per-area-def total/median/coverage."""
    joined = demolished.join(attrs, on="building_id", how="left")
    n = pl.len().alias("n_buildings")
    aggs = [n, pl.col("year").is_not_null().sum().alias("n_dated")]
    for a in AREA_DEFS:
        col = pl.col(f"area_{a}")
        aggs += [
            col.sum().alias(f"m2_{a}"),
            col.median().alias(f"median_m2_{a}"),
            (col.is_not_null().mean() * 100).alias(f"coverage_pct_{a}"),
        ]
    return joined.select(aggs).collect().insert_column(0, pl.Series("variant", [label]))


def annual(label: str, demolished: pl.LazyFrame, attrs: pl.LazyFrame) -> pl.DataFrame:
    """variant × year: count + m² per area def (only dated buildings contribute)."""
    joined = demolished.join(attrs, on="building_id", how="left").filter(
        pl.col("year").is_not_null()
    )
    aggs = [pl.len().alias("n_buildings")] + [
        pl.col(f"area_{a}").sum().alias(f"m2_{a}") for a in AREA_DEFS
    ]
    out = joined.group_by("year").agg(aggs).sort("year").collect()
    return out.insert_column(0, pl.Series("variant", [label] * out.height))


def by_region(label: str, demolished: pl.LazyFrame, attrs: pl.LazyFrame) -> pl.DataFrame:
    """variant × region: count + etageareal m²."""
    joined = demolished.join(attrs, on="building_id", how="left")
    out = (
        joined.group_by("region_name")
        .agg(
            pl.len().alias("n_buildings"),
            pl.col("area_etage").sum().alias("m2_etage"),
        )
        .sort("region_name")
        .collect()
    )
    return out.insert_column(0, pl.Series("variant", [label] * out.height))


def overlap() -> pl.DataFrame:
    """Pairwise intersection + Jaccard among the 7 base indicators (axis off)."""
    sets = {
        i.id: i.build().select("building_id").collect()["building_id"]
        for i in ind.all_indicators()
    }
    rows = []
    ids = list(sets)
    for a in ids:
        sa = set(sets[a])
        for b in ids:
            sb = set(sets[b])
            inter = len(sa & sb)
            union = len(sa | sb)
            rows.append(
                {
                    "a": a,
                    "b": b,
                    "intersection": inter,
                    "jaccard": inter / union if union else 0.0,
                }
            )
    return pl.DataFrame(rows)


# --- Driver -----------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bygning", default=ind.BYGNING_PATH)
    ap.add_argument("--sagsniveau", default=ind.SAGSNIVEAU_PATH)
    ap.add_argument("--bbrsag", default=ind.BBRSAG_PATH)
    args = ap.parse_args()
    ind.BYGNING_PATH = args.bygning
    ind.SAGSNIVEAU_PATH = args.sagsniveau
    ind.BBRSAG_PATH = args.bbrsag

    RESULTS.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)

    print("Rolling up per-building attributes …")
    attrs = build_attributes().collect().lazy()  # materialise once, reuse across variants

    variants = ind.all_variants()
    summaries, annuals, regions = [], [], []
    for label, demolished in variants:
        print(f"  {label} …")
        summaries.append(summarise(label, demolished, attrs))
        annuals.append(annual(label, demolished, attrs))
        regions.append(by_region(label, demolished, attrs))

    summary_df = pl.concat(summaries)
    annual_df = pl.concat(annuals)
    region_df = pl.concat(regions)

    summary_df.write_csv(RESULTS / "ablation_summary.csv")
    annual_df.write_csv(RESULTS / "annual.csv")
    region_df.write_csv(RESULTS / "by_region.csv")

    print("Computing indicator overlap …")
    overlap_df = overlap()
    overlap_df.write_csv(RESULTS / "overlap.csv")

    print("Rendering figures …")
    base = [i.id for i in ind.all_indicators()]  # base indicators only, for readability
    plotting.set_style()
    plotting.annual_lines(
        annual_df, "n_buildings", "Demolished buildings",
        "Annual demolition count by indicator", FIGURES / "annual_counts", base,
    )
    plotting.annual_lines(
        annual_df, "m2_etage", "Demolished floor area (m²)",
        "Annual demolished floor area by indicator", FIGURES / "annual_area_etage", base,
    )
    plotting.area_definition_bars(
        summary_df, AREA_DEFS,
        "Area-definition sensitivity: same indicator, three area columns",
        FIGURES / "area_definition_sensitivity", base,
    )
    plotting.overlap_heatmap(
        overlap_df, "Indicator overlap (Jaccard)", FIGURES / "overlap_heatmap",
    )

    print("\nSummary:")
    with pl.Config(tbl_cols=-1, tbl_width_chars=200, fmt_float="full"):
        print(summary_df)
    print(f"\nWrote tables + figures under {RESULTS}")


if __name__ == "__main__":
    main()
