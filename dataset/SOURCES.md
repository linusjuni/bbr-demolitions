# Data Sources & Provenance

## Raw BBR extract (Datafordeler grunddata, full temporal history)

- `bygning.parquet` — building level (`status`, `forretningsproces`, area, `region_name`,
  use-code, construction year). Source for D1–D3 and all carry-through attributes.
- `sagsniveau.parquet` — case↔building join table (`sagstype`, `stamdataBygning`, `byggesag`).
- `bbrsag.parquet` — case level (`sag002Byggesagsdato`, `sag010FuldførelseAfByggeri`).

Registration-history floor: 2017-06-02, but `virkningFra` is backdated, so demolition
years legitimately reach back to ~2000. Raw BBR column names, UTC datetimes.

## KMD / Andersen demolition extract

- `andersen_raw.csv` — the pre-made demolition extract KMD produced for Andersen &
  Negendahl (2022/2023). **152,300 rows, 149,013 distinct buildings**, Feb 2000 – Jun 2020.
  Carries the building UUID (`id_lokalId`) plus `290 Sagstype`, status codes, dates and
  BBR area columns.
- **Every row is `Sagstype = 32`** (total demolition). All 149,013 distinct buildings join
  into our extract (100%). Its own date (`virkningFra`) is missing for 28,204 rows.
  Used as an **external reference** for 2011–2019 (each side dated by its own date,
  matching ignores the year), not ground truth — see `src/kmd_comparison.py` and
  [`docs/indicators.md`](../docs/indicators.md#reproducing-the-kmdandersen-extract--its-sagstype-32).

## Statistics Denmark BYGB34 (building-stock floor area)

- `bygb34.csv` — BYGB34 "Areas of the building stock" (table updated 2026-03-27),
  downloaded 2026-11-10 from the DST API (`POST https://api.statbank.dk/v1/data`,
  `format=BULK`, `lang=en`, `valuePresentation=CodeAndValue`).
  Selection: OMRÅDE = 000 All Denmark; ANVEND, AREALTYPE, OPFØRELSESÅR, Tid = all.
  47,588 rows (empty combinations are omitted by DST). Unit: 1,000 m².
  Stock on 1 January of each year, 2011–2026; small buildings (garages,
  carports, outhouses) are included only from 2011.
- AREALTYPE: 1 floorspace above basement, 2 floorspace in basement,
  3 industrial/commercial, 4 dwelling area.
- Not committed (`dataset/` is git-ignored); re-download with the request above.
- `bygb12.csv` — BYGB12 "Buildings" (number of buildings; same statistic,
  "Bygningsopgørelsen", same update 2026-03-27), downloaded 2026-11-10 with the same
  request (OMRÅDE = 000; EJER, ANVEND, AREALINT, Tid = all). 14,199 rows, 2011–2026.
  Sum over all categories, 1 January 2026: 4,945,385 buildings.

## Committed dataset

TODO: publish a reproducibility subset alongside the article.
