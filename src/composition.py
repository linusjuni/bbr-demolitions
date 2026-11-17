"""Demolished buildings by building use and construction period (Results 3.2).

Implements Methodology 2.4 P4: for each building, the most recent use code and
construction year (last non-null value by effect date, as ``ablation.py``); use codes
grouped into eight groups (manuscript ``tab:app-building-use-mapping``; detailed codes
share the group of their first two digits, 2.4 P5); construction years in ten-year
periods from 1900, one group before 1900, one group from 2020; buildings with no use
code, and buildings whose construction year is missing or a placeholder, in their own
groups. For each indicator and group: mean number of demolished buildings and mean
demolished total floor area per year over the main comparison period (2018–2025).

Placeholder construction years (``PLACEHOLDER``): missing, 0 or below, 1000 (added
automatically from satellite images and maps), and years after the data (2106). This
is the rule ``ablation.py`` and the old appendix used. Other odd years (1–9, 1100,
1111) are rare and counted as real; ``main`` prints how many fall in 2018–2025.

Outputs (``results/``):
    composition_2018_2025.csv   indicator × axis × group: mean buildings/yr, mean m²/yr,
                                shares of the indicator's totals

Run:  ``.venv/bin/python src/composition.py``
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

import indicators as ind

_ROOT = Path(__file__).resolve().parent.parent
RESULTS = _ROOT / "results"
PERIOD = (2018, 2025)
LAST_DATA_YEAR = 2026

USE_GROUPS = [  # (group, use codes) — manuscript tab:app-building-use-mapping
    ("Housing", [110, 120, 121, 122, 130, 131, 132, 140, 150, 160, 185, 190]),
    ("Agriculture", [210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 970]),
    ("Production and energy", [220, 221, 222, 223, 229, 230, 231, 232, 233, 234, 239, 290]),
    ("Transport", [310, 311, 312, 313, 314, 315, 319]),
    ("Commerce and services", [320, 321, 322, 323, 324, 325, 329, 330, 331, 332, 333,
                               334, 339, 390]),
    ("Institutions", [410, 411, 412, 413, 414, 415, 416, 419, 420, 421, 422, 429, 430,
                      431, 432, 433, 439, 440, 441, 442, 443, 444, 449, 451, 490]),
    ("Leisure", [510, 520, 521, 522, 523, 529, 530, 531, 532, 533, 534, 535, 539, 540,
                 585, 590]),
    ("Outbuildings and other", [910, 920, 930, 940, 950, 960, 990, 999]),
]
NO_USE = "No use code"
UNMAPPED = "Unmapped use code"  # must stay empty; checked in main and the tests
USE_ORDER = [g for g, _ in USE_GROUPS] + [NO_USE]

PERIOD_ORDER = (
    ["Before 1900"]
    + [f"{d}–{d + 9}" for d in range(1900, 2020, 10)]
    + ["2020 onwards", "Missing or placeholder"]
)


def _use_group() -> pl.Expr:
    code = pl.col("use_code")
    expr = pl.when(code.is_null()).then(pl.lit(NO_USE))
    for group, codes in USE_GROUPS:
        expr = expr.when(code.is_in(codes)).then(pl.lit(group))
    return expr.otherwise(pl.lit(UNMAPPED)).alias("use_group")


def _period() -> pl.Expr:
    y = pl.col("construction_year")
    placeholder = y.is_null() | (y <= 0) | (y == 1000) | (y > LAST_DATA_YEAR)
    decade = (y // 10) * 10
    return (
        pl.when(placeholder).then(pl.lit("Missing or placeholder"))
        .when(y < 1900).then(pl.lit("Before 1900"))
        .when(y >= 2020).then(pl.lit("2020 onwards"))
        .otherwise(decade.cast(pl.String) + "–" + (decade + 9).cast(pl.String))
        .alias("period")
    )


def building_attributes() -> pl.DataFrame:
    """One row per building: most recent total floor area, use code, construction year."""
    cols = {
        "byg038SamletBygningsareal": "area_total",
        "byg021BygningensAnvendelse": "use_code",
        "byg026Opførelsesår": "construction_year",
    }
    return (
        pl.scan_parquet(ind.BYGNING_PATH)
        .select("id_lokalId", "virkningFra", *cols)
        .sort("virkningFra")
        .group_by("id_lokalId")
        .agg([pl.col(c).drop_nulls().last().alias(a) for c, a in cols.items()])
        .rename({"id_lokalId": "building_id"})
        .with_columns(_use_group(), _period())
        .collect()
    )


def composition(attrs: pl.DataFrame) -> pl.DataFrame:
    """indicator × axis × group: mean buildings and total floor area per year, 2018–2025."""
    lo, hi = PERIOD
    n_years = hi - lo + 1
    out = []
    for i in ind.all_indicators():
        d = (
            i.build().filter(pl.col("year").is_between(lo, hi)).collect()
            .join(attrs, on="building_id", how="left")
        )
        for axis, col, order in [("use", "use_group", USE_ORDER),
                                 ("period", "period", PERIOD_ORDER)]:
            g = (
                d.group_by(col)
                .agg(
                    (pl.len() / n_years).alias("buildings_per_year"),
                    (pl.col("area_total").fill_null(0).sum() / n_years)
                    .alias("m2_per_year"),
                )
                .rename({col: "group"})
            )
            full = pl.DataFrame({"group": order}).join(g, on="group", how="left").fill_null(0)
            extra = g.filter(~pl.col("group").is_in(order))  # e.g. unmapped codes
            full = pl.concat([full, extra])
            out.append(
                full.with_columns(
                    pl.lit(i.id).alias("indicator"),
                    pl.lit(axis).alias("axis"),
                    (100 * pl.col("buildings_per_year") / pl.col("buildings_per_year").sum())
                    .alias("buildings_share_pct"),
                    (100 * pl.col("m2_per_year") / pl.col("m2_per_year").sum())
                    .alias("m2_share_pct"),
                ).select("indicator", "axis", "group", "buildings_per_year",
                         "m2_per_year", "buildings_share_pct", "m2_share_pct")
            )
    return pl.concat(out)


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    attrs = building_attributes()
    unmapped = attrs.filter(pl.col("use_group") == UNMAPPED)
    print(f"buildings with an unmapped use code: {unmapped.height}")
    neg = attrs.filter(pl.col("area_total") < 0).height
    print(f"buildings with a negative total floor area (all records): {neg:,}")
    comp = composition(attrs)
    comp.write_csv(RESULTS / "composition_2018_2025.csv")
    with pl.Config(tbl_rows=-1, tbl_cols=-1, tbl_width_chars=160, float_precision=3):
        print(comp)
    # Odd construction years counted as real, in D1 2018–2025 (for the record).
    d1 = ind.d1().filter(pl.col("year").is_between(*PERIOD)).collect().join(
        attrs, on="building_id", how="left")
    y = d1["construction_year"]
    print("D1 2018–2025 odd years counted as real: 1–9:", y.is_between(1, 9).sum(),
          "1100:", (y == 1100).sum(), "1111:", (y == 1111).sum())


if __name__ == "__main__":
    main()
