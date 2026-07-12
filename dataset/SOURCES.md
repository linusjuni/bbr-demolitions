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

## Statistics Denmark BYGB34 — building-stock floor area (rate denominator)

- `BYGB34_*.csv` — **BYGB34** "Bygningsbestandens areal efter område, opførelsesår,
  arealtype, anvendelse og tid", downloaded **2026-07-12** from Statistikbanken
  (www.statistikbanken.dk/bygb34).
- **Selection:** Hele landet × all 28 opførelsesår bins × all 4 arealtyper (Samlet
  etageareal, Kælderareal, Erhvervsareal, Boligareal) × all 29 anvendelser × all years
  **2011–2026**. 3,248 data rows, zero missing cells (verified). **Unit: 1,000 m².**
- **Format:** DST hierarchical matrix CSV — ISO-8859-1, semicolon-separated, CRLF, sparse
  row labels in 4 leading columns. Parsed by `src/rates.py:parse_bygb34` (validated
  against the label cross-product and the sanity totals below).
- **Reference date is 1 January** ("Referencetidspunktet er 1. januar" — DST
  statistikdokumentation for Bygningsopgørelsen), so the year-*t* column is the stock at
  the START of year *t*; the 2026 column = end-of-2025 stock. **The table only exists
  from 2011 onward** (confirmed via the DST API) — 2010 is not downloadable, by anyone.
- **Field semantics (DST TIMES declarations):** *Samlet etageareal* = etageareal
  (BYG.38 / BBR felt 216 = `byg038`) **+ tagetagens samlede areal** (utilised attic);
  basement is the separate *Kælderareal*. *Boligareal* = felt 217 = `byg039`;
  *Erhvervsareal* = `byg040`. Hence the matched rate pairings in `src/rates.py`.
  DST imputes nothing ("Der imputeres ingen værdier").
- **Quirk:** 63 small negative cells in the component arealtyper (Bolig/Erhverv only;
  worst −81,000 m² vs a ~650M m² national total). Kept as published so our sums equal
  DST's own aggregates; `src/rates.py` bounds-checks them.
- Parse sanity anchors: national Samlet etageareal 2018 = 753,873 (×1,000 m²);
  Boligareal+Erhvervsareal 2018 = 678,229 (×1,000 m²).

## Committed dataset

TODO: publish a reproducibility subset alongside the article.
