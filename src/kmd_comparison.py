"""Compare every indicator with the Andersen demolition list (the KMD extract).

The list (`dataset/andersen_raw.csv`, 152,300 rows, 149,013 distinct buildings) was
extracted from BBR by the register's administrator for Andersen et al. (2022). Every
row is a whole-demolition case (`290 Sagstype` = 32), and every building carries the
same ID as in the public data, so the list can be compared with each indicator
building by building. It is a reference, not ground truth.

## How the comparison is made (each side keeps its own dates)

The list and the indicators date demolitions differently: the list has its own date
per case (`virkningFra`, missing for 28,204 rows), and the indicators take their years
from different events. Forcing one date on both sides would drop every building that
lacks that date and flatter some indicators (the earlier version dated both sides by
the first status-10 date, which dropped exactly the buildings that make D2/D4/D6
differ from D3/D5). So each side decides by its own date which buildings fall in the
period, and the matching ignores the year:

- **recall** = of the list buildings whose list date (earliest per building) falls in
  the period, the share the indicator counts *in any year*;
- **precision** = of the indicator's buildings whose own year falls in the period, the
  share that is *anywhere* in the list (dated or not).

"In any year" means the indicator built with its period opened wide (same code, see
``any_year``). This matters: 3,951 list buildings dated 2010–2011 by the list are first
historical on 2000-02-05 (the conversion date) in our data, so the indicators dated by
the historical mark place them in 2000, outside the full period.

No Jaccard index: the two sides are selected by different dates.

Run:  ``.venv/bin/python src/kmd_comparison.py``                 (2011–2019)
      ``.venv/bin/python src/kmd_comparison.py --window 2011 2019``
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import polars as pl

import indicators as ind

_ROOT = Path(__file__).resolve().parent.parent
KMD_PATH = str(_ROOT / "dataset" / "andersen_raw.csv")
RESULTS = _ROOT / "results"

# The external comparison period: Andersen et al. (2022) start in 2011, and the list
# was extracted in spring 2020, so 2019 is its last full year.
DEFAULT_WINDOW = (2011, 2019)


def load_kmd(path: str = KMD_PATH) -> pl.DataFrame:
    """The raw list with lower-cased ``building_id`` and its own date ``list_date``.

    Raises if the list is not the expected all-``Sagstype 32`` demolition list, since
    that invariant is the basis of the comparison.
    """
    k = pl.read_csv(path, null_values=["NULL"], infer_schema_length=10000)
    sagstypes = set(k["290 Sagstype"].unique())
    if sagstypes != {32}:
        raise ValueError(
            f"Expected KMD extract to be all Sagstype 32; saw {sorted(sagstypes)}"
        )
    return k.with_columns(
        pl.col("id_lokalId").str.to_lowercase().alias("building_id"),
        pl.col("virkningFra").str.to_date("%m/%d/%Y").alias("list_date"),
    )


def list_years(kmd: pl.DataFrame) -> dict[str, int | None]:
    """building_id -> year of the earliest list date (None if the list gives no date)."""
    per_building = kmd.group_by("building_id").agg(pl.col("list_date").min())
    return {
        b: (d.year if d is not None else None)
        for b, d in zip(per_building["building_id"], per_building["list_date"])
    }


@contextmanager
def any_year() -> Iterator[None]:
    """Build indicators with the period opened wide (membership in any year).

    ``indicators._in_window`` and ``indicators.d4`` read ``YEAR_MIN``/``YEAR_MAX`` when
    called, so widening them reuses the indicator definitions unchanged.
    """
    old = ind.YEAR_MIN, ind.YEAR_MAX
    ind.YEAR_MIN, ind.YEAR_MAX = 0, 9999
    try:
        yield
    finally:
        ind.YEAR_MIN, ind.YEAR_MAX = old


def _years(indicator: ind.Indicator) -> dict[str, int | None]:
    df = (
        indicator.build()
        .select(pl.col("building_id").str.to_lowercase(), "year")
        .collect()
    )
    return dict(zip(df["building_id"], df["year"]))


def _in(years: dict[str, int | None], lo: int, hi: int) -> set[str]:
    return {b for b, y in years.items() if y is not None and lo <= y <= hi}


def score(window: tuple[int, int] = DEFAULT_WINDOW, kmd_path: str = KMD_PATH) -> pl.DataFrame:
    """Per-indicator recall and precision against the list (see module docstring)."""
    lo, hi = window
    ly = list_years(load_kmd(kmd_path))
    list_all = set(ly)
    list_in = _in(ly, lo, hi)
    rows = []
    for i in ind.all_indicators():
        own = _in(_years(i), lo, hi)  # as defined in the paper (full period)
        with any_year():
            ever = set(_years(i))  # counted in any year
        found = len(list_in & ever)
        in_list = len(own & list_all)
        rows.append(
            {
                "proxy": i.id,
                "definition": i.description,
                "n_list_in_period": len(list_in),
                "n_list_found": found,
                "recall": found / len(list_in) if list_in else 0.0,
                "n_proxy_in_period": len(own),
                "n_proxy_in_list": in_list,
                "precision": in_list / len(own) if own else 0.0,
            }
        )
    return pl.DataFrame(rows)


def profile_disagreement(
    window: tuple[int, int] = DEFAULT_WINDOW, kmd_path: str = KMD_PATH
) -> pl.DataFrame:
    """Profile where D4 and the list disagree, on the same sets as ``score``.

    ``kmd_only``: list buildings in the period that D4 does not count in any year.
    ``d4_only``: D4 buildings dated in the period that are not in the list.
    ``both``: list buildings in the period that D4 counts.
    """
    lo, hi = window
    ly = list_years(load_kmd(kmd_path))
    list_all, list_in = set(ly), _in(ly, lo, hi)
    d4 = ind.get("D4")
    own = _in(_years(d4), lo, hi)
    with any_year():
        ever = set(_years(d4))
    groups = {"both": list_in & ever, "kmd_only": list_in - ever, "d4_only": own - list_all}

    cased = set(
        ind._demolition_cases()
        .select(pl.col("building_id").str.to_lowercase())
        .collect()
        .to_series()
    )
    # Per-building latest attributes (select the needed columns before grouping).
    byg = (
        pl.scan_parquet(ind.BYGNING_PATH)
        .select(
            "id_lokalId",
            "virkningFra",
            "status",
            "byg021BygningensAnvendelse",
            "byg026Opførelsesår",
            "byg041BebyggetAreal",
        )
        .sort("virkningFra")
        .group_by("id_lokalId")
        .agg(
            (pl.col("status").last() != 10).alias("not_historical_today"),
            pl.col("byg021BygningensAnvendelse").drop_nulls().last().alias("use"),
            pl.col("byg026Opførelsesår").drop_nulls().last().alias("cyear"),
            pl.col("byg041BebyggetAreal").drop_nulls().last().alias("footprint"),
            pl.len().alias("n_versions"),
        )
        .with_columns(pl.col("id_lokalId").str.to_lowercase())
        .collect()
    )
    rows = []
    for name, s in groups.items():
        sub = byg.filter(pl.col("id_lokalId").is_in(list(s)))
        n = sub.height or 1
        rows.append(
            {
                "group": name,
                "n": len(s),
                "has_demolition_case": len(s & cased) / n,
                "null_use": sub["use"].null_count() / n,
                "null_cyear": sub["cyear"].null_count() / n,
                "null_footprint": sub["footprint"].null_count() / n,
                "not_historical_today": sub["not_historical_today"].mean(),
                "median_versions": sub["n_versions"].median(),
            }
        )
    return pl.DataFrame(rows)


def _print(title: str, df: pl.DataFrame) -> None:
    print(f"\n{title}")
    df = df.with_columns(pl.selectors.float().exclude("median_versions").round(3))
    with pl.Config(tbl_hide_dataframe_shape=True, tbl_rows=-1, tbl_cols=-1):
        print(df.drop("definition", strict=False))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kmd", default=KMD_PATH, help="path to andersen_raw.csv")
    ap.add_argument(
        "--window",
        type=int,
        nargs=2,
        metavar=("MIN", "MAX"),
        default=list(DEFAULT_WINDOW),
        help="inclusive period (default 2011 2019)",
    )
    args = ap.parse_args()
    window = (args.window[0], args.window[1])

    kmd = load_kmd(args.kmd)
    n_distinct = kmd["building_id"].n_unique()
    byg = (
        pl.scan_parquet(ind.BYGNING_PATH)
        .select(pl.col("id_lokalId").str.to_lowercase().alias("building_id"))
        .unique()
        .collect()
    )
    present = len(set(kmd["building_id"]) & set(byg["building_id"]))
    print(
        f"List: {kmd.height} rows, {n_distinct} distinct buildings, all Sagstype 32; "
        f"{kmd['list_date'].null_count()} rows without a date.\n"
        f"{present}/{n_distinct} ({100 * present / n_distinct:.1f}%) present in our extract."
    )

    scores = score(window, args.kmd)
    _print(f"Recall and precision, {window[0]}-{window[1]} (each side by its own date):", scores)
    prof = profile_disagreement(window, args.kmd)
    _print("D4-vs-list disagreement profile:", prof)

    RESULTS.mkdir(exist_ok=True)
    scores.with_columns(pl.lit(f"{window[0]}_{window[1]}").alias("period")).write_csv(
        RESULTS / "kmd_comparison.csv"
    )
    prof.write_csv(RESULTS / "kmd_disagreement_profile.csv")
    print(
        f"\nWrote {RESULTS / 'kmd_comparison.csv'} and "
        f"{RESULTS / 'kmd_disagreement_profile.csv'}"
    )


if __name__ == "__main__":
    main()
