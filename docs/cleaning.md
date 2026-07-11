# Cleaning the temporal BBR data

This document describes the first, shared cleaning layer for the three BBR
temporal extracts. Its job is to make the raw files usable and consistent. It
does not decide what counts as a demolition.

## Inputs and outputs

The raw CSV files are kept in `dataset/raw/`:

| Raw file | Clean output | What one row represents |
| --- | --- | --- |
| `BBR_V3_Bygning_TotalDownload_csv_Temporal_688.csv` | `dataset/clean/bygning.parquet` | One historical version of a building record |
| `BBR_V3_BBRSag_TotalDownload_csv_Temporal_688.csv` | `dataset/clean/bbrsag.parquet` | One historical version of a BBR case |
| `BBR_V3_Sagsniveau_TotalDownload_csv_Temporal_688.csv` | `dataset/clean/sagsniveau.parquet` | One historical version of a case-level record |

The files are made by running:

```bash
.venv/bin/python -m src.cleaning.clean_temporal_bbr
```

The command reads from `dataset/raw/` and writes to `dataset/clean/`. Existing
outputs are protected; use `--overwrite` only when intentionally recreating
them. The main command is in `src/cleaning/clean_temporal_bbr.py`.

## What this step does

The implementation is in `src/cleaning/temporal_cleaner.py` and
`src/cleaning/entity_specs.py`.

1. Keeps every row from the temporal source files. A building or case can
   therefore appear many times, once for each historical version.
2. Keeps every source column. The output Parquet files contain the original
   columns as well as the derived columns described below.
3. Converts known date columns to UTC datetimes.
4. Converts known numeric values and BBR codes to integers. This includes
   fields such as `status`, `forretningsproces`, `sagstype`, and
   `byg021BygningensAnvendelse` where they occur.
5. Normalizes identifier columns by trimming whitespace and changing UUIDs to
   lower case. This makes later joins less fragile.
6. Normalizes `kommunekode` to a four-character string, for example `157`
   becomes `0157`.
7. Writes compressed Parquet files using a streaming conversion, so the large
   raw extracts do not need to be held fully in memory.

The conversion is strict. If a non-empty value cannot be converted to its
documented type, the run fails instead of silently changing it to missing data.

## What this step does not do

Nothing is removed from the source tables in this layer:

- No historical rows are collapsed to one row per building or case.
- No columns are dropped.
- No records are filtered by `status`, `forretningsproces`, `sagstype`, or any
  other field.
- No demolition indicator is created and no demolition date is selected.
- `Bygning`, `BBRSag`, and `Sagsniveau` are not joined together.
- Missing source values are not filled in or guessed.

Those are analytical choices that belong in later datasets or analysis code.
Keeping this layer neutral means we can compare several demolition definitions
without having to recreate the raw cleaning step.

## Added columns

Two documented convenience columns are added without replacing the underlying
BBR codes. Their mappings are defined in `src/cleaning/classifications.py`.

| Column | Added to | Meaning |
| --- | --- | --- |
| `region_name` | All three outputs | The Danish region corresponding to `kommunekode`, using Statistics Denmark's 2007 municipality-region classification. |
| `building_use_group` | `bygning.parquet` only | A broad grouping of `byg021BygningensAnvendelse`. The original use code remains in the data. |

`building_use_group` has the following values:

| Group | BBR use-code families |
| --- | --- |
| `Housing` | 110-190 |
| `Agriculture` | 210-219 and 970 |
| `Production & energy` | 220-239 and 290 |
| `Transport` | 310-319 |
| `Commerce & services` | 320-339 and 390 |
| `Institutions` | 410-490, including 416 |
| `Leisure` | 510-590 |
| `Outbuildings & other` | 910-960, 990, and 999 |

The grouping follows the official BBR use-code hierarchy but is still a
research convenience variable, not a claim that there is one uniquely correct
grouping. For example, later analysis can combine `Agriculture` with
`Production & energy`, and `Transport` with `Commerce & services`, to reproduce
the three broad groups used in Droob et al.

## Checks performed

The tests in `tests/test_temporal_cleaner.py` check that rows are preserved,
known fields get the expected types, identifiers are normalized, and the
classification lookups are complete and non-overlapping. After the full
conversion, we also checked that every non-missing municipality code maps to a
region and every non-missing building-use code maps to a use group.

The broader coverage and area assessment is generated separately with
`.venv/bin/python -m src.data_quality` and documented in
`docs/data_quality_report.md`.

The filters applied after candidate-event detection are specified separately in
`docs/analysis_filters.md`.
