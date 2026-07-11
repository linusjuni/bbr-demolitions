from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

import polars as pl

from src.cleaning.classifications import (
    BUILDING_USE_TO_GROUP,
    MUNICIPALITY_TO_REGION,
)
from src.cleaning.temporal_cleaner import clean_entity_csv


COMMON = {
    "datafordelerOpdateringstid": "2025-09-08T06:43:20.602032Z",
    "datafordelerRowId": "33022DB0-58C0-43D0-B7D7-E6E8C0135162",
    "datafordelerRowVersion": "1",
    "datafordelerRegisterImportSequenceNumber": "6028021",
    "forretningshændelse": "Byggesag",
    "forretningsområde": "54.15.05.05",
    "forretningsproces": "3",
    "id_namespace": "http://data.gov.dk/bbr/test",
    "id_lokalId": "78BF44C9-2FCA-4E6A-A742-09E4FB6EDBB5",
    "kommunekode": "157",
    "registreringFra": "2025-09-06T11:16:55.685728Z",
    "registreringsaktør": "BBR",
    "registreringTil": "",
    "virkningFra": "2025-09-06T11:16:55.685728Z",
    "virkningsaktør": "Registerfører",
    "virkningTil": "",
    "status": "10",
}


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class TemporalCleanerTests(unittest.TestCase):
    def test_bygning_preserves_rows_and_types_known_columns(self) -> None:
        row = {
            **COMMON,
            "byg021BygningensAnvendelse": "210",
            "byg026Opførelsesår": "1945",
            "byg038SamletBygningsareal": "123",
            "byg094Revisionsdato": "2024-01-02T00:00:00Z",
            "byg133KildeTilKoordinatsæt": "K",
            "byg137BanedanmarkBygværksnummer": "00123",
            "byg500Notatlinjer": "retain this",
        }
        second = {**row, "status": "6", "virkningFra": "2020-01-01T00:00:00Z"}
        self._assert_clean(
            "bygning",
            [row, second],
            expected_integer="byg038SamletBygningsareal",
            expected_datetime="byg094Revisionsdato",
        )

    def test_bbrsag_types_case_dates_without_dropping_fields(self) -> None:
        row = {
            **COMMON,
            "sag001Byggesagsnummer": "2024-123",
            "sag002Byggesagsdato": "2024-01-01T00:00:00Z",
            "sag010FuldførelseAfByggeri": "2024-06-01T00:00:00Z",
            "sag012Byggesagskode": "6",
            "sag008FærdigtBygningsareal": "50",
        }
        self._assert_clean(
            "bbrsag",
            [row],
            expected_integer="sag008FærdigtBygningsareal",
            expected_datetime="sag010FuldførelseAfByggeri",
        )

    def test_sagsniveau_normalizes_relation_ids(self) -> None:
        row = {
            **COMMON,
            "niveautype": "2",
            "sagstype": "32",
            "stamdataBygning": "3AC15310-CBAE-4F2D-B513-9F6148DDCCB1",
            "sagsdataBygning": "E3A375BC-4AC1-4292-9623-97DF85FC09FB",
            "byggesag": "0FE3EC70-818F-4335-9445-26626CE42E8A",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.csv"
            output = root / "output.parquet"
            write_csv(source, [row])
            clean_entity_csv(source, output, "sagsniveau")
            result = pl.read_parquet(output)

        self.assertEqual(result["sagstype"].dtype, pl.Int32)
        self.assertEqual(
            result["stamdataBygning"][0],
            "3ac15310-cbae-4f2d-b513-9f6148ddccb1",
        )
        self.assertEqual(result["kommunekode"][0], "0157")

    def _assert_clean(
        self,
        entity: str,
        rows: list[dict[str, str]],
        *,
        expected_integer: str,
        expected_datetime: str,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.csv"
            output = root / "output.parquet"
            write_csv(source, rows)
            result_info = clean_entity_csv(source, output, entity)
            result = pl.read_parquet(output)

        self.assertEqual(result.height, len(rows))
        derived_columns = ["region_name"]
        if entity == "bygning":
            derived_columns.append("building_use_group")
        self.assertEqual(result_info.columns, (*rows[0], *derived_columns))
        self.assertEqual(result[expected_integer].dtype, pl.Int64)
        self.assertEqual(result[expected_datetime].dtype, pl.Datetime("us", "UTC"))
        self.assertEqual(result["status"].dtype, pl.Int32)
        self.assertEqual(result["region_name"][0], "Region Hovedstaden")
        if entity == "bygning":
            self.assertEqual(result["byg133KildeTilKoordinatsæt"][0], "K")
            self.assertEqual(result["byg137BanedanmarkBygværksnummer"][0], "00123")
            self.assertEqual(result["building_use_group"][0], "Agriculture")
        self.assertEqual(
            result["id_lokalId"][0], "78bf44c9-2fca-4e6a-a742-09e4fb6edbb5"
        )
        self.assertEqual(result["kommunekode"][0], "0157")

    def test_classifications_cover_official_codes_and_code_416(self) -> None:
        self.assertEqual(len(MUNICIPALITY_TO_REGION), 99)
        self.assertEqual(len(BUILDING_USE_TO_GROUP), 105)
        self.assertEqual(BUILDING_USE_TO_GROUP[416], "Institutions")


if __name__ == "__main__":
    unittest.main()
