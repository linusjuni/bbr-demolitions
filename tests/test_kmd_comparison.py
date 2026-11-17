"""Invariants of the comparison with the Andersen list (``src/kmd_comparison.py``).

Slow (builds every indicator twice, about half a minute). Skipped if the dataset or
the list is absent.
Run: ``.venv/bin/python -m unittest tests.test_kmd_comparison -v``
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import indicators as ind  # noqa: E402  (same module object kmd_comparison uses)
import kmd_comparison as kc  # noqa: E402

DATA_OK = Path(ind.BYGNING_PATH).exists() and Path(kc.KMD_PATH).exists()


@unittest.skipUnless(DATA_OK, "dataset/ or the list not available")
class KmdComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        df = kc.score()
        cls.s = {r["proxy"]: r for r in df.iter_rows(named=True)}

    def test_any_year_restores_period(self):
        before = ind.YEAR_MIN, ind.YEAR_MAX
        with kc.any_year():
            self.assertNotEqual((ind.YEAR_MIN, ind.YEAR_MAX), before)
        self.assertEqual((ind.YEAR_MIN, ind.YEAR_MAX), before)

    def test_every_list_building_is_in_the_register(self):
        kmd = set(kc.load_kmd()["building_id"])
        byg = set(
            pl.scan_parquet(ind.BYGNING_PATH)
            .select(pl.col("id_lokalId").str.to_lowercase())
            .unique()
            .collect()
            .to_series()
        )
        self.assertEqual(kmd - byg, set())

    def test_scores_are_shares(self):
        for r in self.s.values():
            self.assertTrue(0.0 <= r["recall"] <= 1.0)
            self.assertTrue(0.0 <= r["precision"] <= 1.0)

    def test_same_list_side_for_all(self):
        self.assertEqual(len({r["n_list_in_period"] for r in self.s.values()}), 1)

    def test_d4_dated_equals_d5(self):
        # D4's undated buildings have no year, so its dated set is D5's.
        self.assertEqual(self.s["D4"]["n_proxy_in_period"], self.s["D5"]["n_proxy_in_period"])
        self.assertEqual(self.s["D4"]["precision"], self.s["D5"]["precision"])

    def test_recall_follows_set_inclusion(self):
        # In any year: D3 within D1 and D2, D5 within D1 and D4, D6 within D4.
        r = {k: v["recall"] for k, v in self.s.items()}
        self.assertGreaterEqual(r["D1"], r["D3"])
        self.assertGreaterEqual(r["D2"], r["D3"])
        self.assertGreaterEqual(r["D1"], r["D5"])
        self.assertGreaterEqual(r["D4"], r["D5"])
        self.assertGreaterEqual(r["D4"], r["D6"])


if __name__ == "__main__":
    unittest.main()
