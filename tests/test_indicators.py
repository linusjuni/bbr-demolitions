"""Checks of the D1-D6 definitions against the real extract.

Two kinds of check:

1. An independent re-implementation of every rule, written differently from
   ``src/indicators.py`` (eager, set-based; D1 "today" via the last version by
   effect date instead of the open version), must give exactly the same
   buildings and years.
2. Invariants the definitions must satisfy (D3 = D1 ∩ D2, D5 = D1 ∩ D4, ...).

Slow (reads the full parquets, a few minutes). Skipped if ``dataset/`` is absent.
Run: ``.venv/bin/python -m unittest tests.test_indicators -v``
"""

from __future__ import annotations

import unittest
from pathlib import Path

import polars as pl

from src import indicators as ind

DATA = Path(ind.BYGNING_PATH)
LO, HI = ind.YEAR_MIN, ind.YEAR_MAX


def _frame(lf: pl.LazyFrame) -> dict[str, int | None]:
    df = lf.collect()
    assert df["building_id"].n_unique() == df.height, "one row per building"
    return dict(zip(df["building_id"], df["year"]))


def _keep(year: int | None) -> bool:
    return year is None or LO <= year <= HI


@unittest.skipUnless(DATA.exists(), "dataset/ not available")
class IndicatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        b = pl.scan_parquet(ind.BYGNING_PATH).select(
            "id_lokalId", "status", "forretningsproces", "virkningFra"
        )
        sn = pl.scan_parquet(ind.SAGSNIVEAU_PATH).select(
            "sagstype", "stamdataBygning", "sagsdataBygning", "byggesag"
        )
        sag = pl.scan_parquet(ind.BBRSAG_PATH).select(
            "id_lokalId", "sag002Byggesagsdato", "sag007Henlæggelse"
        )

        # --- independent D1: last version by effect date has status 10 ---
        last = b.sort("virkningFra").group_by("id_lokalId").agg(pl.col("status").last()).collect()
        hist_now = set(last.filter(pl.col("status") == 10)["id_lokalId"])
        first10 = (
            b.filter(pl.col("status") == 10).group_by("id_lokalId")
            .agg(pl.col("virkningFra").min().dt.year()).collect()
        )
        first10 = dict(zip(first10["id_lokalId"], first10["virkningFra"]))
        pairs = sn.filter(
            pl.col("sagsdataBygning").is_not_null() & pl.col("stamdataBygning").is_not_null()
        ).select("sagsdataBygning", "stamdataBygning").unique().collect()
        case_rec = {
            s: t for s, t in zip(pairs["sagsdataBygning"], pairs["stamdataBygning"]) if s != t
        }
        cls.case_records = set(case_rec)
        hist_now -= cls.case_records  # a case's own record is not a building
        cls.hist_now = hist_now
        cls.d1 = {k: first10[k] for k in hist_now if _keep(first10[k])}

        # --- independent D2: own-record date, else completed (status 9) case
        # record date, else first case-record date ---
        p3 = b.filter(pl.col("forretningsproces") == 3).collect()
        own, case_done, case_first = {}, {}, {}
        for i, v, s in zip(p3["id_lokalId"], p3["virkningFra"], p3["status"]):
            if i in case_rec:
                k = case_rec[i]
                case_first[k] = min(case_first.get(k, v), v)
                if s == 9:
                    case_done[k] = min(case_done.get(k, v), v)
            else:
                own[i] = min(own.get(i, v), v)
        cls.own_p3_year = {k: v.year for k, v in own.items()}
        cls.case_done_year = {k: v.year for k, v in case_done.items() if k not in own}
        d2 = {
            k: (own.get(k) or case_done.get(k) or case_first[k]).year
            for k in set(own) | set(case_first)
        }
        cls.d2 = {k: y for k, y in d2.items() if _keep(y)}

        # --- independent cases: cancelled = any version with sag007 set ---
        cancelled = set(
            sag.filter(pl.col("sag007Henlæggelse").is_not_null())
            .select("id_lokalId").unique().collect()["id_lokalId"]
        )
        notify = (
            sag.group_by("id_lokalId").agg(pl.col("sag002Byggesagsdato").min()).collect()
        )
        notify = dict(zip(notify["id_lokalId"], notify["sag002Byggesagsdato"]))
        links = sn.filter(
            (pl.col("sagstype") == 32) & pl.col("stamdataBygning").is_not_null()
        ).select("stamdataBygning", "byggesag").unique().collect()
        total_case_buildings: set[str] = set()
        first_notify: dict[str, object] = {}
        for bld, case in zip(links["stamdataBygning"], links["byggesag"]):
            if case in cancelled:
                continue
            total_case_buildings.add(bld)
            d = notify.get(case)
            if d is not None:
                first_notify[bld] = min(first_notify.get(bld, d), d)
        cls.cancelled = cancelled
        cls.total_case_buildings = total_case_buildings
        cls.d4 = {
            k: (first10[k] if k in hist_now else None)
            for k in total_case_buildings
        }
        # undated buildings only if their case was notified within the period
        cls.d4 = {
            k: y for k, y in cls.d4.items()
            if (y is not None and LO <= y <= HI)
            or (y is None and k in first_notify and LO <= first_notify[k].year <= HI)
        }
        cls.d6 = {k: d.year for k, d in first_notify.items() if LO <= d.year <= HI}

        # --- code under test ---
        cls.code = {i.id: _frame(i.build()) for i in ind.all_indicators()}

    # 1. independent implementation agrees exactly
    def test_d1_matches(self):
        self.assertEqual(self.code["D1"], self.d1)

    def test_d2_matches(self):
        self.assertEqual(self.code["D2"], self.d2)

    def test_d4_matches(self):
        self.assertEqual(self.code["D4"], self.d4)

    def test_d6_matches(self):
        self.assertEqual(self.code["D6"], self.d6)

    # 2. invariants
    def test_d1_is_historical_today(self):
        self.assertTrue(set(self.code["D1"]) <= self.hist_now)

    def test_d3_is_d1_and_d2(self):
        d1, d2, d3 = self.code["D1"], self.code["D2"], self.code["D3"]
        self.assertEqual(set(d3), set(d1) & set(d2))
        self.assertTrue(all(d3[k] == d1[k] for k in d3))

    def test_d5_is_d1_and_d4(self):
        d1, d4, d5 = self.code["D1"], self.code["D4"], self.code["D5"]
        self.assertEqual(set(d5), set(d1) & set(d4))
        self.assertTrue(all(d5[k] == d1[k] for k in d5))

    def test_d4_dated_equals_d5(self):
        d4 = {k for k, y in self.code["D4"].items() if y is not None}
        self.assertEqual(d4, set(self.code["D5"]))

    def test_d4_undated_notified_in_period(self):
        d6_all = self.code["D6"]
        undated = [k for k, y in self.code["D4"].items() if y is None]
        self.assertGreater(len(undated), 20_000)
        self.assertTrue(all(k in d6_all for k in undated))

    def test_d6_within_d4_rule(self):
        self.assertTrue(set(self.code["D6"]) <= self.total_case_buildings)

    def test_no_case_record_counted_as_building(self):
        for k in ("D1", "D2", "D3", "D4", "D5", "D6"):
            self.assertFalse(set(self.code[k]) & self.case_records, k)

    def test_d2_case_dated_by_completion(self):
        d2 = self.code["D2"]
        self.assertGreater(len(self.case_done_year), 90_000)
        for k, y in self.case_done_year.items():
            if k in d2:
                self.assertEqual(d2[k], y)

    def test_d2_uses_own_date_first(self):
        d2 = self.code["D2"]
        for k, y in self.own_p3_year.items():
            if k in d2:
                self.assertEqual(d2[k], y)

    def test_years_in_period(self):
        for k, s in self.code.items():
            ys = [y for y in s.values() if y is not None]
            self.assertTrue(all(LO <= y <= HI for y in ys), k)
            if k != "D4":
                self.assertEqual(len(ys), len(s), f"{k} has undated buildings")


if __name__ == "__main__":
    unittest.main()
