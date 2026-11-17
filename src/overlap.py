"""Which buildings the indicators share, and which year they give them (Results 3.2).

Methodology 2.5 compares the indicators with each other in the main comparison period
(2018–2025): two indicators share a building only if both count it in that period. The
pairwise Jaccard index is in ``results/overlap_2018_2025.csv`` (``ablation.py``). This
script adds two views of the same comparison:

- **shared**: for each indicator, its buildings in 2018–2025 split by how many of the
  other indicators also count them in 2018–2025 (none / some / all). D4 and D5 count
  the same buildings in every year, so they form one series ("D4, D5") and each series
  has four others.
- **year differences**: for buildings that both an indicator and D1 count in
  2018–2025 (the same rule as the Jaccard index: shared = counted by both in the
  period), the indicator's year minus D1's year. Methods 2.3 gives the same comparison
  for the full period (D6: 67.9 % earlier, 30.9 % same year).

Outputs (``results/``):
    overlap_shared_2018_2025.csv     series × number of other series that also count it
    overlap_year_difference.csv      indicator vs D1: year difference (clipped to ±3)

Run:  ``.venv/bin/python src/overlap.py``
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

import indicators as ind

_ROOT = Path(__file__).resolve().parent.parent
RESULTS = _ROOT / "results"
PERIOD = (2018, 2025)

# Series as in the figures: D4 and D5 are identical when dated, so one series.
SERIES = {"D1": "D1", "D2": "D2", "D3": "D3", "D4, D5": "D5", "D6": "D6"}


def _in_period(indicator_id: str) -> set[str]:
    lo, hi = PERIOD
    return set(
        ind.get(indicator_id)
        .build()
        .filter(pl.col("year").is_between(lo, hi))
        .select("building_id")
        .collect()
        .to_series()
    )


def shared() -> pl.DataFrame:
    """series × n_others: buildings in 2018–2025 also counted by n of the other series."""
    sets = {s: _in_period(i) for s, i in SERIES.items()}
    rows = []
    for s, own in sets.items():
        others = [sets[o] for o in sets if o != s]
        counts = [0] * (len(others) + 1)
        for b in own:
            counts[sum(b in o for o in others)] += 1
        for n, c in enumerate(counts):
            rows.append({"series": s, "n_others": n, "of_others": len(others),
                         "buildings": c, "total": len(own),
                         "share_pct": 100 * c / len(own)})
    return pl.DataFrame(rows)


def year_difference() -> pl.DataFrame:
    """indicator vs D1: share of shared buildings by year difference (indicator − D1)."""
    lo, hi = PERIOD
    years = {
        i: ind.get(i).build().filter(pl.col("year").is_between(lo, hi)).collect()
        for i in ["D1", "D2", "D3", "D5", "D6"]
    }
    rows = []
    for i in ["D2", "D3", "D5", "D6"]:
        j = years[i].join(years["D1"], on="building_id", suffix="_d1")
        diff = (j["year"] - j["year_d1"]).clip(-3, 3)
        for d, c in diff.value_counts().sort(diff.name).rows():
            rows.append({"indicator": "D4, D5" if i == "D5" else i, "difference": d,
                         "buildings": c, "total": j.height,
                         "share_pct": 100 * c / j.height})
    return pl.DataFrame(rows)


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    s = shared()
    s.write_csv(RESULTS / "overlap_shared_2018_2025.csv")
    y = year_difference()
    y.write_csv(RESULTS / "overlap_year_difference.csv")
    with pl.Config(tbl_rows=-1, tbl_cols=-1, tbl_width_chars=160):
        print(s)
        print(y)


if __name__ == "__main__":
    main()
