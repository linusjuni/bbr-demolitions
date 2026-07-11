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
  into our extract (100%). Used as a **window-matched external reference**, not ground
  truth — see `src/kmd_comparison.py` and
  [`docs/indicators.md`](../docs/indicators.md#reproducing-the-kmdandersen-extract--its-sagstype-32).

## Committed dataset

TODO: publish a reproducibility subset alongside the article.
