# The ablation pipeline — what we built and why

This documents the runnable pipeline that turns the demolition indicators into the
numbers and figures the article reports. It is the companion to `docs/indicators.md`
(which defines *why* the indicators disagree) and to the code in `src/`.

- **Definitions** — `src/indicators.py` (the D1–D6 set + the discontinued-code axis).
- **Driver** — `src/ablation.py` (sweeps the 12-variant grid, writes tables).
- **Rates** — `src/rates.py` (BYGB34 denominator → demolition rate vs stock).
- **Figures** — `src/plotting.py` (seaborn, English labels, importable).

Run the whole thing (~60 s on the full extract; the rate step reads `annual.csv`, so it
runs second):

```bash
.venv/bin/python src/ablation.py
.venv/bin/python src/rates.py
```

## What the pipeline computes

For every one of the **12 variants** (`D1`…`D6` and their `-exdisc` counterparts,
from `indicators.all_variants()`) the driver attaches outcome measures and writes:

| File | Grain | Contents |
|---|---|---|
| `results/ablation_summary.csv` | one row / variant | count, plus total m² / median m² / coverage % under **each** of 3 area definitions |
| `results/annual.csv` | variant × year | count + m² per area definition (dated buildings only) |
| `results/by_region.csv` | variant × region | count + floor-area m² (uses the `region_name` column) |
| `results/overlap.csv` | indicator × indicator | pairwise intersection + Jaccard, 6 base indicators, full 2000-2025 window |
| `results/overlap_2018_2025.csv` | indicator × indicator | same overlap calculation, restricted to dated 2018-2025 memberships |
| `results/figures/*.png` + `*.pdf` | — | `annual_counts`, `annual_area_total`, `overlap_heatmap`, `overlap_heatmap_2018_2025` |

The indicators themselves return only `building_id` + `year` (the *membership* of the
demolished set). Everything else — area, use-code, region, construction year — is rolled
up **once** from `bygning.parquet` in `build_attributes()`, using each building's **last
known non-null value** over its full temporal history. That rollup is aggregation
plumbing, not a demolition decision, so it lives in the driver and never inside an
indicator (keeping the indicators pure, per the "no opaque contract" principle in
`docs/indicators.md`).

## The area decision (the one that needed a judgment call)

### The problem, measured on this extract

On the ~451k `status = 10` buildings, taking the **max area over each building's whole
history** (best case), the area columns have wildly different completeness:

| Column | Meaning | Null on demolished buildings |
|---|---|---|
| `byg041BebyggetAreal` | ground **footprint** (birdseye) | **0.2%** — essentially complete |
| `byg038SamletBygningsareal` | total building area | **~54%** |
| `byg039…Bolig` + `byg040…Erhverv` | floor area (BUILD's basis) | **~54–85%** |

The nulls are **genuine** — max-over-history recovers only ~5.6k of 247k, so they are
not "blanked on the historical exit row." The intuitive m² column (total / floor area,
what every paper reports) is missing for the **majority** of demolished buildings, while
the only complete column (footprint) is a *different physical quantity* (ground area, not
floor area across storeys).

### What the papers do (we checked)

- **Andersen & Negendahl (2023), *Lifespan prediction of existing building typologies*** —
  explicit **listwise deletion**: *"the data has been sorted to improve its quality by
  removing buildings with missing registrations of demolition date, floor area or use."*
  Complete-case, **no imputation**. Their cleaned 104,927 cases sum to 17.1 M m².
- **BUILD / Social- og Boligstyrelsen (2025), *Omfanget af … nedrivning*** — reports
  **etageareal = bolig + erhverv**, sums the available area, and openly caveats that the
  total is *"formentlig overvurderet … mangelfulde eller fejlbehæftede."* No imputation
  described.

So the field standard is **complete-case: sum the area you have, drop nothing else,
impute nothing.**

### What we did

We followed that standard **and made its hidden cost visible**. For each variant and each
area column we report `sum()` (polars skips nulls → a complete-case sum for that column),
`median()`, and **`coverage_pct`** (share of the variant's buildings with a non-null
value). Concretely, in `summarise()`:

```python
col.sum()                        # total m² — nulls skipped, never imputed
col.median()
(col.is_not_null().mean() * 100) # coverage %
```

Two deliberate departures from the papers, both toward transparency:

1. **We keep all three area definitions side by side** (footprint / total / etage) instead
   of silently committing to one. Their divergence is a reported result (the article's
   secondary question 5), not a nuisance to resolve.
2. **We report coverage next to every total.** On Andersen's KMD data "drop missing" lost a
   small minority; on this Datafordeler extract it silently drops **>50%**, so a bare
   "total m²" would read as a national figure while covering ~46% of buildings. Coverage %
   makes that explicit; footprint (near-complete) is the coverage anchor.

**We did not** reduce everything to footprint/birdseye, and **we did not** drop building
rows — a building with null total-area still counts in `n_buildings` and still contributes
its footprint; it just doesn't add to the total/etage *sum*. No imputation anywhere.

Example (`D1`, from `ablation_summary.csv`):

| area def | total m² | coverage |
|---|---|---|
| footprint | 50.1 M | 99.8% |
| total | 44.7 M | 46.5% |
| etage | 47.5 M | 46.5% |

Read as: footprint is trustworthy but a different quantity; total/etage are "of the ~46%
we can see."

## Erroneous-value cleaning

We model **demolitions, not lifespan**, so the only values that can corrupt an output are
the ones we aggregate: the **demolition date** and the **area**. Those we clean. The
**construction year is left RAW** — it is a covariate we never aggregate on, so its errors
(0, medieval, or the auto-generated GIS marker `1000`) are harmless here, and nulling them
would only discard real demolitions' metadata for no gain. We **coerce to null, never drop
buildings** — so no indicator's count changes and `coverage_pct` stays honest.

| Rule | Action | Rationale |
|---|---|---|
| footprint, total, etage | `≤ 0 → null` | negative area is impossible; zero ground/floor area on a standing building is "unregistered", not a real 0 (fixes coverage%/median, not the sums). Same rule for all three — footprint is not treated inconsistently |
| construction year | **kept raw** | not aggregated; errors can't corrupt a demolition output |
| auto-generated year 1000 | **flagged, not removed** (`autogenerated`) | lets a future lifespan / construction-period analysis drop them (Andersen 2023 does) without baking it in |
| future demolition dates | removed by the year window | the modelled date is clipped in `indicators._in_window`; empirically there are none beyond the current year (max = 2026, `>2026` = 0) |

`cleaning_report()` writes `results/cleaning_report.csv` — values removed per rule, for the
whole stock and **per demolition indicator** (year-1000 shown as a *kept* flag for context):

| scope | n | negative total | zero total | missing total | year-1000 (kept) |
|---|---:|---:|---:|---:|---:|
| ALL buildings | 6,250,075 | 17,844 | 107,404 | 3,123,967 | 454,739 |
| D1 status=10 | 436,194 | 0 | 8,427 | 233,304 | 38,923 |
| D2 process=3 | 225,706 | **6,197** | 3,874 | 152,939 | 11,805 |
| D3 | 99,664 | 0 | 3,552 | 37,742 | 11,633 |
| D4 sagstype=32 | 237,012 | 0 | 6,184 | 90,000 | 16,077 |
| D5 status10 ∩ 32 | 200,634 | 0 | 3,877 | 77,498 | 13,063 |
| D6 total case, dated | 231,962 | 0 | 5,960 | 87,410 | 15,658 |

Findings:
- **Non-positive footprints are exclusive to D2** (9,342; zero everywhere else) — another D2/
  process-3 anomaly (it already had the lowest footprint coverage). Removing the negatives
  among them *raised* D2's footprint total (15.7M→16.9M m²), which they had been dragging down.
- Zero/negative total & etage hit ~3–5% of each indicator, lowering area coverage (e.g. D1
  total coverage 46.5%→44.6%) but not the m² sums.
- **~9% of every indicator's demolitions carry the year-1000 GIS marker** (38,923 of D1).
  Irrelevant to counts/area (kept), but flagged because it would inflate any *lifespan*
  estimate — the point at which it should be dropped, not here.

**Judgment call (confirmed, kept visible):** non-positive areas read as missing, not a real 0.
Construction-year errors are deliberately *not* cleaned — that would be a lifespan concern,
and this study models demolitions.

## Held-fixed confounds

Per `docs/indicators.md`, everything except the indicator is frozen so it can't confound
the comparison:

- **Window** — 2000–2025 inclusive, clamped in `indicators._in_window` (undated matches
  kept, so `D4` doesn't collapse into `D5`).
- **Discontinued-code exclusion** — an orthogonal on/off axis (`-exdisc`), never baked into
  an indicator.
- **Building attributes** — rolled up identically (same last-non-null rule) for every
  variant.

## Headline results already visible

- **The discontinued-code exclusion is an *area* story, not a count story.** `-exdisc` cuts
  `D1`'s count 31% (436k→302k) but its total m² **80%** (44.7M→9.1M): those discontinued
  round-number codes are the big agricultural buildings — matching BUILD's "landbrug
  dominates the m²" finding.
- **The two canonical proxies barely agree.** `D1` (status-10) vs `D2` (process-3) Jaccard
  = **0.18**; the case-based indicators (`D4`/`D5`/`D6`) cluster tightly at 0.85–0.92.
- **Area coverage itself splits by indicator** — floor area is present for ~46% of `D1`
  buildings but ~62% of the case-based ones, and `D2`'s footprint coverage is an anomalous
  ~51% vs ~99.8% elsewhere.

## The rate vs stock step (`src/rates.py`)

Turns the annual demolished m² into **demolition rates** — % of national stock floor
area per year — against the Statistics Denmark **BYGB34** stock denominator (the same
denominator as the Rune PhD and Andersen 2023; provenance in `dataset/SOURCES.md`).
BYGB34 exists only from 2011, so rates exist for **2011–2025** and the PhD's 2010–2019
window can only be matched as 2011–2019.

Decisions (Theodor, 2026-07-12):

- **Field-matched pairings, never crossed.** Primary rate = `m2_etage` (byg039+byg040)
  ÷ BYGB34 *Boligareal + Erhvervsareal* — exact BBR-field match on both sides and
  BUILD's own area basis. Secondary = `m2_total` (byg038) ÷ *Samlet etageareal* (which
  per DST = byg038 + utilised attic, so slightly wide). Footprint gets **no rate**
  (BYGB34 has no footprint stock).
- **Year convention:** demolitions of year *t* ÷ stock at 1 January of year *t*
  (BYGB34's reference date).
- **Complete-case, coverage reported** — same convention as the m² tables above; the
  anchors were computed the same way, which is what makes the rates comparable. All
  rates are therefore **lower bounds**; `coverage_pct` sits beside every rate in
  `rates_summary.csv`.
- **BUILD's pre-1999 numerator cut is NOT applied** (decided 2026-07-12 — it would have
  been the pipeline's first use of the raw construction year as a filter). Over BUILD's
  2012–2023 window our numerator is accordingly wider than theirs.
- **The headline window is 2018–2025** (decided 2026-07-12) — the article's clean-years
  window: `D3` 0.250% → `D1` 0.441%, a 1.8-fold spread. The other windows stay in
  `rates_summary.csv` for the anchor comparisons only.

| File | Grain | Contents |
|---|---|---|
| `results/stock_national.csv` | year | parsed BYGB34 national stock (m²) per arealtype |
| `results/rates_annual.csv` | variant × year | m², stock and rate under both pairings |
| `results/rates_summary.csv` | variant × window | mean annual rate + m²/yr + coverage, for 2011–2019 (PhD), 2012–2023 (BUILD), 2018–2025 (clean years), 2011–2025 |
| `results/rates_spread.csv` | window × pairing | min/max variant + **fold spread** (the headline) |
| `results/figures/rate_vs_stock.*` | — | annual rate lines vs the published 0.26%/0.3% anchor levels |

Headline numbers now on file (primary pairing, base indicators):

- **The PhD anchor reproduces:** `D4` (KMD/`sagstype=32`) 2011–2019 = **0.254 %/yr**
  vs the PhD's ~0.26% (`D5` 0.256%, `D6` 0.254%). Window-matched one year short, stated
  above.
- **Indicator spread:** 2011–2019 runs `D3` 0.064% → `D1` 0.444% (**6.9-fold**);
  the clean-years window 2018–2025 runs `D3` 0.250% → `D1` 0.441% (**1.8-fold**).
  Adding the `-exdisc` axis widens 2011–2019 to 30-fold (`D3-exdisc` 0.015% → `D1`).
- In the figure `D4` is invisible under `D6` — their dated annual series are identical
  (caveat 1 below), a built-in consistency check. `D2`/`D3` sit near zero before
  2016/2017 (the register-history floor), which drags their early-window means down.

## The KMD/Andersen extract is reproducible — and it's `sagstype 32`

We hold the raw KMD extract (`dataset/andersen_raw.csv`, 152,300 rows) with building UUIDs,
so it is no longer a black box. `src/kmd_comparison.py` scores every proxy against it
(→ `results/kmd_comparison.csv`); full write-up in
[`docs/indicators.md`](indicators.md#reproducing-the-kmdandersen-extract--its-sagstype-32).

Two axes must be kept separate here — conflating them is easy:

1. **Which buildings (demolition membership).** We do **not** copy Andersen (their
   *filtering* recipe is unpublished). We build transparent proxies and then *measure*
   against KMD. Result, window-matched to 2011–2019: KMD is the **total-demolition-case**
   signal — `D4`/`D5`/`D6` all reproduce it at Jaccard 0.985–0.991, while `D1`
   (status-10) is a strict **superset** (100% recall, 47% precision) and `D2` (process-3) a
   severe **undercount** (24% recall). Membership can't single out *one* case variant
   (D4≈D5≈D6), so the claim is "KMD = the total-demolition case family," D4/D5 tightest.
2. **How much area (missing-data handling).** *This* is the axis where we follow the papers
   (complete-case, no imputation — see "The area decision" above) — it is a portable
   convention, independent of how the demolished set was chosen.

## Known caveats (open, not bugs)

1. **`D4` undated members are absent from the time series.** Its year comes from
   status-10; a building with a demolition case but no status-10 exit has `year = null`, so
   it counts in the *totals* but not in `annual.csv` / the trend figures (`D4`'s dated
   subset ≈ `D6`). **Decided 2026-07-12 (Theodor): kept as is — no re-dating, no fallback;
   the consequence (`D4 ≡ D6` in every annual/rate output) is documented, not "fixed".**
   The considered alternative — dating case buildings by the case's own `sag002` date —
   was rejected because that date is the *filing* of the demolition case, not the
   demolition: measured on this extract it matches the status-10 year exactly for only
   27.6% of buildings (median 1 year earlier, 8% later), and re-dating would collapse
   `D5` into `D6` (~97% identical) and erase the D4↔D6 dating contrast. The case-dated
   view of the case family already exists in the set as `D6`.
2. **Year-2000 pile-up.** Backdated `virkningFra` below the 2000 clamp all lands on 2000
   (the `D1` spike in `annual_counts`). Candidate fix: a `≤2000` bucket.

## Not yet done

- ~~⭐ Outcome × indicator range — the paper's headline~~ **DONE 2026-07-12** — see "The
  rate vs stock step" above: `rates_summary.csv` (mean m²/yr + rate per window) and
  `rates_spread.csv` (the min–max fold spread) now exist, and the PhD's ~0.26% anchor
  reproduces under `D4`. Decided 2026-07-12: headline window = 2018–2025; BUILD's
  pre-1999 numerator cut is not applied; the D4/D5 undated-year question is closed as
  "keep as is, document" (caveat 1) — nothing further is open on this thread.
- **Fold KMD scoring into the main run** — `src/kmd_comparison.py` runs standalone; it
  could emit its table alongside the other `results/` outputs from `ablation.py`.
- **BOSSINF scoring** — the one *authoritative* slice (grant-funded demolitions) where a
  real precision/recall could be read per variant. KMD is a reference, BOSSINF is truth.
- **Typology grouping** — `use_code` is carried raw; an `anvendelse`→typology grouping
  (a research judgment) is not yet applied.
