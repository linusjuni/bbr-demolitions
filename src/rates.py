"""Demolition rates: demolished housing + business area / the same area of all buildings.

Implements Methodology 2.4 P3 and the published-estimate comparisons of 2.5 (last
paragraph) of the manuscript:

- **Numerator**: for each building, its most recent housing area (``byg039``) and
  most recent business area (``byg040``), each the last non-null value by effect date,
  added (a missing value counts as 0). Summed over the buildings an indicator dates to
  year *t*.
- **Denominator**: Statistics Denmark BYGB34, housing + business area of all buildings
  in Denmark on 1 January of year *t* (AREALTYPE 3 + 4, all uses, all construction
  years; ``dataset/bygb34.csv``, unit 1,000 m²). BYGB34 starts in 2011, so rates exist
  for 2011–2025 only.
- **Mean rate** over a period = mean of the annual rates.

Also computed (2.5, last paragraph):

- the administrator's extract (``dataset/andersen_raw.csv``) measured the same way:
  each extract building dated by its earliest extract date, area from our data (main)
  and, as a check, from the extract's own area columns;
- Jensen et al. (2025) comparison: demolished housing + business area per year,
  2012–2023, for buildings built before 1999, under every indicator (the paper uses D1).

Outputs (``results/``):
    rates_annual.csv          indicator × year 2011–2025: buildings, m², stock, rate
    rates_summary.csv         indicator × period (2018–2025, 2011–2019): mean rate, range, m²/yr
    rates_extract.csv         the extract's rate, 2011–2019: our way (two area sources)
                              and Andersen et al.'s way (floor area above the basement)
    rates_jensen.csv          indicator: mean m²/yr and rate 2012–2023, built before 1999 and all

Run:  ``.venv/bin/python src/rates.py``
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

import indicators as ind
import kmd_comparison as kmd

_ROOT = Path(__file__).resolve().parent.parent
RESULTS = _ROOT / "results"
BYGB34_PATH = _ROOT / "dataset" / "bygb34.csv"

RATE_YEARS = (2011, 2025)  # BYGB34 starts in 2011; the full period ends in 2025
PERIODS = {"2018_2025": (2018, 2025), "2011_2019": (2011, 2019)}
JENSEN_YEARS = (2012, 2023)
JENSEN_BUILT_BEFORE = 1999


def building_areas() -> pl.DataFrame:
    """One row per building: most recent housing area, business area and construction year.

    Only the needed columns are read before sorting and grouping (the table has
    ~33.8 M versions). Each value is the last non-null one by effect date, the same
    rule ``ablation.py`` uses for the total floor area.
    """
    cols = {
        "byg039BygningensSamledeBoligAreal": "area_housing",
        "byg040BygningensSamledeErhvervsAreal": "area_business",
        "byg026Opførelsesår": "construction_year",
    }
    return (
        pl.scan_parquet(ind.BYGNING_PATH)
        .select("id_lokalId", "virkningFra", *cols)
        .sort("virkningFra")
        .group_by("id_lokalId")
        .agg([pl.col(c).drop_nulls().last().alias(a) for c, a in cols.items()])
        .select(
            pl.col("id_lokalId").str.to_lowercase().alias("building_id"),
            "area_housing",
            "area_business",
            (pl.col("area_housing").fill_null(0) + pl.col("area_business").fill_null(0))
            .alias("area_hb"),
            "construction_year",
        )
        .collect()
    )


def national_stock(area_types: tuple[str, ...] = ("3 ", "4 ")) -> pl.DataFrame:
    """year -> area of all buildings on 1 January (m²), BYGB34.

    Default: housing + business area (AREALTYPE 3 + 4), the denominator of every rate
    in the paper. ``("1 ",)`` = floor area above the basement, the denominator
    Andersen et al. (2022) used; only for reproducing their 0.24 %.
    """
    return (
        pl.read_csv(BYGB34_PATH, separator=";", infer_schema_length=0)
        .filter(pl.col("AREALTYPE").str.slice(0, 2).is_in(list(area_types)))
        .select(
            pl.col("TID").str.slice(0, 4).cast(pl.Int32).alias("year"),
            (pl.col("INDHOLD").cast(pl.Float64) * 1000).alias("stock_m2"),
        )
        .group_by("year")
        .agg(pl.col("stock_m2").sum())
        .sort("year")
    )


def annual_rates(label: str, dated: pl.DataFrame, areas: pl.DataFrame,
                 stock: pl.DataFrame) -> pl.DataFrame:
    """label × year: buildings, demolished housing + business m², stock, rate (%)."""
    lo, hi = RATE_YEARS
    return (
        dated.filter(pl.col("year").is_between(lo, hi))
        .join(areas.select("building_id", "area_hb"), on="building_id", how="left")
        .group_by("year")
        .agg(
            pl.len().alias("n_buildings"),
            pl.col("area_hb").fill_null(0).sum().alias("m2_housing_business"),
            (pl.col("area_hb").fill_null(0) > 0).sum().alias("buildings_with_area"),
        )
        .join(stock, on="year", how="left")
        .with_columns(
            pl.lit(label).alias("indicator"),
            (pl.col("m2_housing_business") / pl.col("stock_m2") * 100).alias("rate_pct"),
        )
        .select("indicator", "year", "n_buildings", "buildings_with_area",
                "m2_housing_business", "stock_m2", "rate_pct")
        .sort("year")
    )


def summarise(annual: pl.DataFrame) -> pl.DataFrame:
    """indicator × period: mean, min and max annual rate, mean m²/yr and buildings/yr."""
    rows = []
    for name, (lo, hi) in PERIODS.items():
        rows.append(
            annual.filter(pl.col("year").is_between(lo, hi))
            .group_by("indicator")
            .agg(
                pl.col("rate_pct").mean().alias("mean_rate_pct"),
                pl.col("rate_pct").min().alias("min_rate_pct"),
                pl.col("rate_pct").max().alias("max_rate_pct"),
                pl.col("m2_housing_business").mean().alias("mean_m2_per_year"),
                pl.col("n_buildings").mean().alias("mean_buildings_per_year"),
                pl.len().alias("n_years"),
            )
            .with_columns(pl.lit(name).alias("period"))
        )
    return pl.concat(rows).sort("period", "indicator")


def _dated(indicator: ind.Indicator) -> pl.DataFrame:
    return (
        indicator.build()
        .filter(pl.col("year").is_not_null())
        .select(pl.col("building_id").str.to_lowercase(), "year")
        .collect()
    )


def extract_rates(areas: pl.DataFrame, stock: pl.DataFrame) -> pl.DataFrame:
    """The extract's rate in 2011–2019, measured as for the indicators.

    Each extract building is dated by its earliest extract date (as in the extract
    comparison); undated buildings are left out. Area source ``our_data`` = the
    building's most recent housing + business area in our data; ``extract_columns`` =
    the extract's own housing + business columns on the row with the earliest date;
    ``above_basement`` = the extract's own columns over the floor area above the
    basement of all buildings, as Andersen et al. (2022) calculated it.
    """
    lo, hi = PERIODS["2011_2019"]
    k = kmd.load_kmd()
    first = (
        k.filter(pl.col("list_date").is_not_null())
        .sort("list_date")
        .group_by("building_id")
        .agg(
            pl.col("list_date").first().dt.year().alias("year"),
            (
                pl.col("byg039BygningensSamledeBoligAreal").fill_null(0)
                + pl.col("byg040BygningensSamledeErhvervsAreal").fill_null(0)
            ).first().alias("area_hb"),
        )
    )
    own_columns = first.select("building_id", "area_hb")
    dated = first.select("building_id", "year")
    runs = [
        ("extract_our_data", areas, stock),
        ("extract_extract_columns", own_columns, stock),
        # Andersen et al.'s own setup: the extract's area over the floor area above
        # the basement of all buildings (reproduces their 0.24 %, see handover).
        ("extract_above_basement", own_columns, national_stock(("1 ",))),
    ]
    return pl.concat(
        annual_rates(label, dated, a, st).filter(pl.col("year").is_between(lo, hi))
        for label, a, st in runs
    )


def jensen_comparison(areas: pl.DataFrame, dated: dict[str, pl.DataFrame],
                      stock: pl.DataFrame) -> pl.DataFrame:
    """indicator: mean demolished housing + business m²/yr and rate in 2012–2023.

    ``built_before_1999``: construction year known and below 1999 (as Jensen et al.,
    who count only buildings built before 1999; placeholder years such as 1000 are
    below 1999 and therefore included, as they would be in a plain year filter).
    The rate divides by the housing + business area of ALL buildings on 1 January,
    as Jensen et al. do (their 674 million m², 2.2 / 674 ≈ 0.3 %); mean of the
    annual rates, as elsewhere.
    """
    lo, hi = JENSEN_YEARS
    n_years = hi - lo + 1
    years = pl.DataFrame({"year": list(range(lo, hi + 1))}, schema={"year": pl.Int32})

    def yearly(frame: pl.DataFrame) -> pl.DataFrame:
        per_year = frame.group_by("year").agg(pl.col("area_hb").fill_null(0).sum())
        return (
            years.join(per_year.with_columns(pl.col("year").cast(pl.Int32)),
                       on="year", how="left")
            .fill_null(0)
            .join(stock, on="year", how="left")
            .with_columns((pl.col("area_hb") / pl.col("stock_m2") * 100).alias("rate"))
        )

    rows = []
    for label, d in dated.items():
        j = d.filter(pl.col("year").is_between(lo, hi)).join(
            areas, on="building_id", how="left"
        )
        old = j.filter(pl.col("construction_year") < JENSEN_BUILT_BEFORE)
        y_old, y_all = yearly(old), yearly(j)
        rows.append(
            {
                "indicator": label,
                "years": f"{lo}-{hi}",
                "mean_m2_per_year_built_before_1999": y_old["area_hb"].sum() / n_years,
                "mean_rate_pct_built_before_1999": y_old["rate"].mean(),
                "mean_m2_per_year_all": y_all["area_hb"].sum() / n_years,
                "mean_rate_pct_all": y_all["rate"].mean(),
                "buildings_built_before_1999": old.height,
                "buildings_all": j.height,
            }
        )
    return pl.DataFrame(rows)


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    print("Rolling up housing + business area per building …")
    areas = building_areas()
    neg = areas.filter((pl.col("area_housing") < 0) | (pl.col("area_business") < 0)).height
    print(f"  {areas.height:,} buildings; {neg:,} with a negative housing or business area")
    stock = national_stock()

    dated = {}
    annual = []
    for i in ind.all_indicators():
        print(f"  {i.id} …")
        dated[i.id] = _dated(i)
        annual.append(annual_rates(i.id, dated[i.id], areas, stock))
    annual_df = pl.concat(annual)
    annual_df.write_csv(RESULTS / "rates_annual.csv")
    summary_df = summarise(annual_df)
    summary_df.write_csv(RESULTS / "rates_summary.csv")

    print("Extract's rate …")
    extract_df = extract_rates(areas, stock)
    extract_df.write_csv(RESULTS / "rates_extract.csv")

    print("Jensen et al. comparison …")
    jensen_df = jensen_comparison(areas, dated, stock)
    jensen_df.write_csv(RESULTS / "rates_jensen.csv")

    with pl.Config(tbl_cols=-1, tbl_rows=-1, tbl_width_chars=200):
        print(summary_df)
        print(extract_df.group_by("indicator").agg(
            pl.col("rate_pct").mean().alias("mean"), pl.col("rate_pct").min().alias("min"),
            pl.col("rate_pct").max().alias("max")))
        print(jensen_df)


if __name__ == "__main__":
    main()
