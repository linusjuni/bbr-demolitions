"""Score every proxy indicator against the KMD / Andersen demolition extract.

`docs/indicators.md` long treated the KMD extract (the pre-made list behind Andersen &
Negendahl 2022/2023) as an **opaque** proxy whose recipe could not be reproduced or
audited. We now hold the raw extract itself (`dataset/andersen_raw.csv`, 152,300 rows),
**with building UUIDs**, so we can compare it to our transparent proxies on set
membership and partly reverse-engineer its recipe.

What this script establishes, empirically:

1. **The extract's core signal is `Sagstype = 32`** (Nedrivning hel / total demolition) —
   *every* row carries it. So KMD is a total-demolition-case list, i.e. the same signal as
   our D4/D6, NOT the register-exit `status = 10` (D1).
2. **All 149,013 distinct KMD buildings are present in our 2017+ extract** (backdated
   `virkningFra` keeps the records), so the join is clean and total.
3. **Window-matched, D4 reproduces KMD to ~99%** (recall 99.7%, precision 99.4%,
   Jaccard 0.99). D1 (status=10) has 100% recall but ~47% precision — a strict *superset*,
   not KMD. So the "opaque" extract is reproducible after all: it is `sagstype = 32`.

## Why the window matters (and the one-clock rule)

KMD spans Feb 2000 – Jun 2020 and the paper discards pre-2011; our proxies run 2000–2025
unfiltered. Comparing them raw makes each proxy's legitimate post-2020 / pre-2011
demolitions look like false positives, so **precision is meaningless without windowing**
(un-windowed, D4 precision reads 63%; windowed to 2011–2019 it is 99%).

To avoid dating the two sides on different clocks, both KMD and every proxy are dated by
the SAME field — our extract's status-10 `virkningFra` year (`indicators._status10_year`).
Consequence: buildings that never reached status-10 (case-only / process-only members)
drop from *both* sides, so within the window D2≡D3 and D4≡D6. That is a fair common clock;
it slightly understates D2's and D4/D5's native reach, but the D4≈KMD headline is robust.

Run:  ``.venv/bin/python src/kmd_comparison.py``            (both raw and windowed tables)
      ``.venv/bin/python src/kmd_comparison.py --window 2011 2019``   (custom window)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl

import indicators as ind

_ROOT = Path(__file__).resolve().parent.parent
KMD_PATH = str(_ROOT / "dataset" / "andersen_raw.csv")
RESULTS = _ROOT / "results"

# Default fair window: post the pre-2011 registration-error era the paper itself excludes,
# and before the mid-2020 extract cutoff (2020 is only partial in the KMD data).
DEFAULT_WINDOW = (2011, 2019)


def load_kmd(path: str = KMD_PATH) -> pl.DataFrame:
    """The raw KMD extract with lower-cased ``building_id`` (matches our parquet casing).

    Raises if the extract is not the expected all-``Sagstype 32`` demolition list, since
    that invariant is the whole basis of the comparison.
    """
    k = pl.read_csv(path, null_values=["NULL"], infer_schema_length=10000)
    sagstypes = set(k["290 Sagstype"].unique())
    if sagstypes != {32}:
        raise ValueError(
            f"Expected KMD extract to be all Sagstype 32; saw {sorted(sagstypes)}"
        )
    return k.with_columns(pl.col("id_lokalId").str.to_lowercase().alias("building_id"))


def _status10_clock() -> dict[str, int]:
    """building_id (lower-cased) -> status-10 virkningFra year, the shared dating clock."""
    s10 = (
        ind._status10_year()
        .select(pl.col("building_id").str.to_lowercase(), "year")
        .collect()
    )
    return dict(zip(s10["building_id"], s10["year"]))


def _proxy_set(indicator: ind.Indicator) -> set[str]:
    return set(
        indicator.build()
        .select(pl.col("building_id").str.to_lowercase())
        .collect()
        .to_series()
    )


def score(window: tuple[int, int] | None, kmd_path: str = KMD_PATH) -> pl.DataFrame:
    """Per-proxy recall / precision / Jaccard against the KMD set.

    ``window=None`` compares full sets as-is (recall meaningful, precision NOT — see the
    module docstring). A ``(min, max)`` window dates both sides on the shared status-10
    clock and restricts to that inclusive year range, making precision fair.
    """
    kmd = set(load_kmd(kmd_path)["building_id"])
    clock = _status10_clock() if window else None

    def restrict(s: set[str]) -> set[str]:
        if window is None:
            return s
        lo, hi = window
        return {b for b in s if (y := clock.get(b)) is not None and lo <= y <= hi}

    kmd_w = restrict(kmd)
    rows = []
    for i in ind.all_indicators():
        s = restrict(_proxy_set(i))
        inter = len(s & kmd_w)
        union = len(s | kmd_w)
        rows.append(
            {
                "proxy": i.id,
                "definition": i.description,
                "n_proxy": len(s),
                "n_intersection": inter,
                "recall_of_kmd": inter / len(kmd_w) if kmd_w else 0.0,
                "precision": inter / len(s) if s else 0.0,
                "jaccard": inter / union if union else 0.0,
            }
        )
    return pl.DataFrame(rows)


def profile_disagreement(
    window: tuple[int, int] = DEFAULT_WINDOW, kmd_path: str = KMD_PATH
) -> pl.DataFrame:
    """Profile the buildings where D4 and KMD disagree, vs the ones they agree on.

    Records the finding written up in `docs/indicators.md` ("The ~1% where D4 and KMD
    disagree is structured"): the mismatch is not random. `kmd_only` (D4 misses) are
    case-less status-10 ghosts, ~63% empty stubs; `d4_only` (KMD omitted) are clean,
    fully-populated demolition-case buildings. One row per group with the diagnostics.
    """
    lo, hi = window
    clock = _status10_clock()

    def restrict(s: set[str]) -> set[str]:
        return {b for b in s if (y := clock.get(b)) is not None and lo <= y <= hi}

    kmd = restrict(set(load_kmd(kmd_path)["building_id"]))
    d4 = restrict(_proxy_set(ind.get("D4")))
    groups = {"both": kmd & d4, "kmd_only": kmd - d4, "d4_only": d4 - kmd}

    # Which buildings carry a linked demolition case at all (why D4 keeps/drops them).
    cased = set(
        _demol_case_buildings := ind._demolition_cases()
        .select(pl.col("building_id").str.to_lowercase())
        .collect()
        .to_series()
    )
    # Per-building latest attributes.
    byg = (
        pl.scan_parquet(ind.BYGNING_PATH)
        .sort("virkningFra")
        .group_by("id_lokalId")
        .agg(
            (pl.col("status").last() != 10).alias("reactivated"),
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
                "n": sub.height,
                "has_demolition_case": len(s & cased) / n,
                "null_use": sub["use"].null_count() / n,
                "null_cyear": sub["cyear"].null_count() / n,
                "null_footprint": sub["footprint"].null_count() / n,
                "reactivated": sub["reactivated"].mean(),
                "median_versions": sub["n_versions"].median(),
            }
        )
    return pl.DataFrame(rows)


def _print(title: str, df: pl.DataFrame) -> None:
    print(f"\n{title}")
    if {"proxy", "recall_of_kmd"}.issubset(df.columns):  # a score() table
        df = df.select(
            "proxy",
            "n_proxy",
            "n_intersection",
            (pl.col("recall_of_kmd") * 100).round(1).alias("recall%"),
            (pl.col("precision") * 100).round(1).alias("prec%"),
            pl.col("jaccard").round(3),
        )
    else:  # a profile table — round the float diagnostics to percentages/2dp
        df = df.with_columns(
            pl.selectors.float().exclude("median_versions").round(3)
        )
    with pl.Config(tbl_hide_dataframe_shape=True, tbl_rows=-1):
        print(df)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kmd", default=KMD_PATH, help="path to andersen_raw.csv")
    ap.add_argument(
        "--window",
        type=int,
        nargs=2,
        metavar=("MIN", "MAX"),
        default=list(DEFAULT_WINDOW),
        help="inclusive year window for the fair comparison (default 2011 2019)",
    )
    args = ap.parse_args()

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
        f"KMD extract: {kmd.height} rows, {n_distinct} distinct buildings, "
        f"all Sagstype 32.\n{present}/{n_distinct} "
        f"({100 * present / n_distinct:.1f}%) present in our extract."
    )

    raw = score(window=None, kmd_path=args.kmd)
    windowed = score(window=tuple(args.window), kmd_path=args.kmd)
    _print("Raw (NOT window-matched — precision not meaningful):", raw)
    _print(f"Window-matched to {args.window[0]}-{args.window[1]} (status-10 clock):", windowed)

    prof = profile_disagreement(window=tuple(args.window), kmd_path=args.kmd)
    _print("D4-vs-KMD disagreement profile (where they differ, and how):", prof)

    RESULTS.mkdir(exist_ok=True)
    out = pl.concat(
        [
            raw.with_columns(pl.lit("raw").alias("comparison")),
            windowed.with_columns(
                pl.lit(f"window_{args.window[0]}_{args.window[1]}").alias("comparison")
            ),
        ]
    )
    out.write_csv(RESULTS / "kmd_comparison.csv")
    prof.write_csv(RESULTS / "kmd_disagreement_profile.csv")
    print(
        f"\nWrote {RESULTS / 'kmd_comparison.csv'} and "
        f"{RESULTS / 'kmd_disagreement_profile.csv'}"
    )


if __name__ == "__main__":
    main()
