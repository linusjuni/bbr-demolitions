from __future__ import annotations

import unittest

import polars as pl

from src.data_quality import (
    AreaField,
    currently_effective,
    summarize_area_consistency,
    summarize_area_fields,
    summarize_missingness,
)


class DataQualityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = pl.DataFrame(
            {
                "id_lokalId": ["a", "a", "b"],
                "registreringTil": [None, None, None],
                "virkningTil": ["2024-01-01T00:00:00Z", None, None],
                "status": [6, 10, 6],
                "name": ["", "value", None],
                "byg038SamletBygningsareal": [100, 120, None],
                "byg039BygningensSamledeBoligAreal": [80, 100, None],
                "byg040BygningensSamledeErhvervsAreal": [20, 20, None],
                "byg041BebyggetAreal": [100, 60, 30],
                "byg048AndetAreal": [None, None, None],
            }
        ).lazy()

    def test_currently_effective_produces_one_row_per_test_id(self) -> None:
        result = currently_effective(self.frame).collect()
        self.assertEqual(result.height, 2)
        self.assertEqual(result["id_lokalId"].n_unique(), 2)

    def test_missingness_counts_blank_and_null_strings(self) -> None:
        result = summarize_missingness(
            "test", "all", self.frame, ("name", "status")
        )
        name = result.filter(pl.col("column") == "name").row(0, named=True)
        self.assertEqual(name["missing_count"], 2)
        self.assertAlmostEqual(name["missing_pct"], 200 / 3)

    def test_area_summary_separates_null_zero_and_negative(self) -> None:
        fields = (
            AreaField("byg038SamletBygningsareal", "Total", "candidate"),
        )
        result = summarize_area_fields("all", self.frame, fields).row(
            0, named=True
        )
        self.assertEqual(result["null_count"], 1)
        self.assertEqual(result["zero_count"], 0)
        self.assertEqual(result["negative_count"], 0)
        self.assertEqual(result["median_m2"], 110)

    def test_area_consistency_reports_availability_and_ratio(self) -> None:
        result = summarize_area_consistency(
            currently_effective(self.frame), "current"
        )
        metrics = {
            row["metric"]: row["value"] for row in result.iter_rows(named=True)
        }
        self.assertEqual(metrics["both_present"], 1)
        self.assertEqual(metrics["footprint_only"], 1)
        self.assertEqual(metrics["total_equals_residential_plus_commercial"], 1)
        self.assertEqual(metrics["floor_to_footprint_ratio_median"], 2.0)


if __name__ == "__main__":
    unittest.main()
