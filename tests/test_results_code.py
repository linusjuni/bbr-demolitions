"""Invariants of the Results code: ``rates.py``, ``overlap.py``, ``composition.py``.

Each test checks the code against the data or against another, independent output
(``annual.csv`` from ``ablation.py``), so a silent change in one pipeline shows up.
Slow (rolls up the building table and builds the indicators; about a minute).
Skipped if the dataset is absent.
Run: ``.venv/bin/python -m unittest tests.test_results_code -v``
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import composition as comp  # noqa: E402
import indicators as ind  # noqa: E402
import overlap as ov  # noqa: E402
import rates  # noqa: E402

DATA_OK = Path(ind.BYGNING_PATH).exists() and rates.BYGB34_PATH.exists()
ANNUAL = ROOT / "results" / "annual.csv"


@unittest.skipUnless(DATA_OK and ANNUAL.exists(), "dataset/ or results/annual.csv missing")
class ResultsCodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.attrs = comp.building_attributes()
        cls.comp = comp.composition(cls.attrs)
        cls.annual = pl.read_csv(ANNUAL)
        cls.shared = ov.shared()

    # --- rates.py ---------------------------------------------------------------
    def test_stock_matches_statistics_denmark(self):
        # Housing + business area of all buildings, 1 Jan (handover / 2.4 P3):
        # 2012 647.9, 2018 678.2, 2023 686.2, 2026 697.1 million m².
        s = dict(rates.national_stock().iter_rows())
        for year, million in {2012: 647.9, 2018: 678.2, 2023: 686.2, 2026: 697.1}.items():
            self.assertAlmostEqual(s[year] / 1e6, million, delta=0.06)
        self.assertEqual(min(s), 2011)

    def test_rate_is_area_over_stock(self):
        areas = rates.building_areas()
        stock = rates.national_stock()
        d1 = rates._dated(ind.get("D1"))
        r = rates.annual_rates("D1", d1, areas, stock).filter(pl.col("year") == 2020)
        row = r.row(0, named=True)
        self.assertAlmostEqual(
            row["rate_pct"], 100 * row["m2_housing_business"] / row["stock_m2"], places=12
        )
        n_2020 = self.annual.filter((pl.col("variant") == "D1") & (pl.col("year") == 2020))
        self.assertEqual(row["n_buildings"], n_2020["n_buildings"][0])

    def test_extract_rates(self):
        # Our way 0.261 %; Andersen et al.'s way 0.232 % (published 0.24 %).
        r = rates.extract_rates(rates.building_areas(), rates.national_stock())
        mean = dict(r.group_by("indicator").agg(pl.col("rate_pct").mean()).iter_rows())
        self.assertAlmostEqual(mean["extract_our_data"], 0.261, delta=0.001)
        self.assertAlmostEqual(mean["extract_above_basement"], 0.232, delta=0.001)
        self.assertEqual(r.filter(pl.col("indicator") == "extract_above_basement").height, 9)

    def test_jensen_comparison(self):
        # D1, built before 1999, 2012–2023: 2.52 million m²/yr, 0.38 % (handover).
        areas = rates.building_areas()
        stock = rates.national_stock()
        d1 = {"D1": rates._dated(ind.get("D1"))}
        r = rates.jensen_comparison(areas, d1, stock).row(0, named=True)
        self.assertAlmostEqual(r["mean_m2_per_year_built_before_1999"] / 1e6, 2.52, delta=0.005)
        self.assertAlmostEqual(r["mean_rate_pct_built_before_1999"], 0.377, delta=0.001)
        self.assertGreater(r["mean_m2_per_year_all"], r["mean_m2_per_year_built_before_1999"])

    # --- composition.py ---------------------------------------------------------
    def test_no_unmapped_use_code(self):
        self.assertEqual(self.attrs.filter(pl.col("use_group") == comp.UNMAPPED).height, 0)

    def test_groups_add_up_to_annual_totals(self):
        lo, hi = comp.PERIOD
        n_years = hi - lo + 1
        for i in ["D1", "D2", "D3", "D4", "D5", "D6"]:
            a = self.annual.filter((pl.col("variant") == i) & pl.col("year").is_between(lo, hi))
            for axis in ("use", "period"):
                c = self.comp.filter((pl.col("indicator") == i) & (pl.col("axis") == axis))
                self.assertAlmostEqual(
                    c["buildings_per_year"].sum(), a["n_buildings"].sum() / n_years, places=6
                )
                self.assertAlmostEqual(
                    c["m2_per_year"].sum(), a["m2_total"].sum() / n_years, delta=1e-3
                )

    def test_periods_are_complete_and_ordered(self):
        c = self.comp.filter((pl.col("indicator") == "D1") & (pl.col("axis") == "period"))
        self.assertEqual(c["group"].to_list(), comp.PERIOD_ORDER)

    def test_placeholder_years(self):
        a = self.attrs
        self.assertTrue(
            (a.filter(pl.col("construction_year") == 1000)["period"]
             == "Missing or placeholder").all()
        )
        self.assertTrue(
            (a.filter(pl.col("construction_year").is_null())["period"]
             == "Missing or placeholder").all()
        )
        self.assertTrue(
            (a.filter(pl.col("construction_year") == 1955)["period"] == "1950–1959").all()
        )

    def test_d4_equals_d5(self):
        a = self.comp.filter(pl.col("indicator") == "D4").drop("indicator")
        b = self.comp.filter(pl.col("indicator") == "D5").drop("indicator")
        self.assertTrue(a.equals(b))

    # --- overlap.py -------------------------------------------------------------
    def test_shares_add_to_100(self):
        for s, g in self.shared.group_by("series"):
            self.assertAlmostEqual(g["share_pct"].sum(), 100.0, places=9)

    def test_intersections_have_no_lone_buildings(self):
        # D3 = D1 ∩ D2 and D5 = D1 ∩ D4: every building is also in D1.
        for s in ("D3", "D4, D5"):
            none = self.shared.filter((pl.col("series") == s) & (pl.col("n_others") == 0))
            self.assertEqual(none["buildings"][0], 0)

    def test_all_shared_is_one_number(self):
        # A building counted by all five series appears as "all others" in each.
        alls = self.shared.filter(pl.col("n_others") == 4)["buildings"].unique()
        self.assertEqual(alls.len(), 1)

    def test_totals_match_jaccard_diagonal(self):
        jac = pl.read_csv(ROOT / "results" / "overlap_2018_2025.csv")
        diag = {r["a"]: r["intersection"] for r in jac.iter_rows(named=True) if r["a"] == r["b"]}
        tot = dict(self.shared.select("series", "total").unique().iter_rows())
        self.assertEqual(tot["D1"], diag["D1"])
        self.assertEqual(tot["D4, D5"], diag["D5"])
        self.assertEqual(tot["D6"], diag["D6"])

    def test_year_difference_rules(self):
        y = ov.year_difference()
        for s in ("D3", "D4, D5"):  # take their year from D1
            d = y.filter(pl.col("indicator") == s)
            self.assertEqual(d["difference"].to_list(), [0])
        d6_later = y.filter((pl.col("indicator") == "D6") & (pl.col("difference") > 0))
        self.assertLess(d6_later["share_pct"].sum(), 0.1)


if __name__ == "__main__":
    unittest.main()
