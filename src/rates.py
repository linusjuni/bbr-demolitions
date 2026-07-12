"""Demolition rate vs stock — the rate benchmark (docs/paper.md, "The rate-vs-stock
benchmark to reproduce").

Numerator: computed HERE, directly from the ``src/indicators.py`` registry (variant ×
year complete-case demolished m²). It used to be read from ``results/annual.csv``, but
commit 774f90a narrowed ``src/ablation.py`` to the byg038 total area only, while the rate
benchmark's PRIMARY pairing is field-matched on byg039+byg040 — so the numerator is built
in this module under the pre-774f90a complete-case area semantics the manuscript
describes (verified 2026-07-12 to reproduce the previous rates exactly for the
unchanged indicators).
Denominator: Statistics Denmark table **BYGB34** (``dataset/BYGB34_*.csv``) — national
building-stock floor area per 1 January, unit 1,000 m². BYGB34 exists only from 2011
onward (confirmed via the DST API), so no rate can be computed for earlier years and the
Rune-PhD window 2010–2019 can only be matched as 2011–2019.

Field-matched numerator ↔ denominator pairings (decided 2026-07-12; never cross-matched):

    rate_etage  m2_etage (byg039+byg040) ÷ (Boligareal + Erhvervsareal)      [PRIMARY]
                Exact BBR-field match on both sides (DST Boligareal = felt 217 = byg039;
                Erhvervsareal = byg040) and BUILD's own area basis — the BUILD/PhD-
                comparable rate.
    rate_total  m2_total (byg038) ÷ Samlet etageareal
                Per DST's TIMES declaration, Samlet etageareal = etageareal (BYG.38 /
                felt 216 = byg038) + utilised attic area — the denominator is slightly
                wider than the numerator field, a mild extra downward bias.
    footprint   NO rate. BYGB34 carries no ground-footprint stock, so byg041 has no
                matched denominator; a crossed rate would mix physical quantities.

Year convention (decided 2026-07-12): demolitions of year *t* ÷ stock at 1 January of
year *t* (BYGB34's reference date is 1 January, so the column-*t* stock is the population
at risk during year *t*). The 2026 column (= end-of-2025 stock) is left unused.

Rates are complete-case **lower bounds**: the numerator sums only buildings with a
non-null area (~45–60% coverage depending on indicator) while the denominator is the
full stock. Nothing is scaled or imputed — this matches how the anchor numbers were
themselves computed (Andersen 2023: listwise deletion; BUILD 2025: sums available area),
which is the point of the benchmark. Variant-level ``coverage_pct`` is carried into
``rates_summary.csv`` so every rate reads next to its coverage.

Caveats inherited from the numerator (docs/ablation.md "Known caveats"):
 - D4's undated members are absent from ``annual.csv`` → its rates are slightly low,
   and D4's annual rates are IDENTICAL to D5's (D4's dated subset = D5 — in the figure
   D4 hides under D5). Decided 2026-07-12: kept as is and documented, no re-dating —
   the case-dated view of the case family is already in the set as D6.
 - BUILD's ~0.3% additionally restricts the *numerator* to pre-1999 buildings; that cut
   is NOT applied (decided 2026-07-12), so over 2012–2023 our numerator is wider.

Reference anchors drawn on the figure (published values, not ours):
 - Rune Andersen PhD: ~0.26 %/yr of stock floor area, KMD/sagstype-32, 2010–2019.
 - BUILD 2025: ~0.3 %/yr, "udgået", pre-1999 buildings, 2012–2023.

Outputs (written under ``results/``):
    stock_national.csv   parsed BYGB34 national stock per year × arealtype (m²)
    rates_annual.csv     variant × year (2011–2025): m², stock and rate, both pairings
    rates_summary.csv    variant × window: mean annual rate, mean m²/yr, coverage
    rates_spread.csv     window × pairing × scope: min/max variant + fold spread
    figures/rate_vs_stock.{png,pdf}

Run:  .venv/bin/python src/rates.py
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import polars as pl

import indicators as ind
import plotting

_ROOT = Path(__file__).resolve().parent.parent
DATASET = _ROOT / "dataset"
RESULTS = _ROOT / "results"
FIGURES = RESULTS / "figures"

BASE_INDICATORS = ["D1", "D2", "D3", "D4", "D5", "D6"]

# DST arealtype labels (ISO-8859-1 in the raw file, decoded on read).
_AT_SAMLET = "Samlet etageareal"
_AT_BOLIG = "Boligareal"
_AT_ERHVERV = "Erhvervsareal"
_AT_KAELDER = "Kælderareal"
_AREALTYPER = {_AT_SAMLET, _AT_BOLIG, _AT_ERHVERV, _AT_KAELDER}

# Reporting windows: (label, first year, last year, why this window).
WINDOWS = [
    ("2011-2019", 2011, 2019, "Rune PhD anchor ~0.26%/yr (their 2010-2019; 2010 not in BYGB34)"),
    ("2012-2023", 2012, 2023, "BUILD anchor ~0.3%/yr (their numerator: pre-1999 buildings only)"),
    ("2018-2025", 2018, 2025, "article clean-years window — HEADLINE window (decided 2026-07-12)"),
    ("2011-2025", 2011, 2025, "full denominator era"),
]

# Published reference values drawn on the figure (source, not result).
ANCHORS = [
    (0.26, "Rune PhD ~0.26% (KMD, 2010-2019)"),
    (0.30, "BUILD ~0.3% (pre-1999, 2012-2023)"),
]


# --- BYGB34 parsing -----------------------------------------------------------
# DST "matrix" CSV: ISO-8859-1, semicolon-separated, CRLF, values in 1,000 m².
# Four sparse leading label columns (område / opførelsesår / arealtype / anvendelse) —
# a label appears once and is implied on the rows below it, so the parser carries the
# last seen value of each level forward.


def find_bygb34(dataset_dir: Path = DATASET) -> Path:
    hits = sorted(dataset_dir.glob("BYGB34_*.csv"))
    if len(hits) != 1:
        raise FileNotFoundError(
            f"expected exactly one dataset/BYGB34_*.csv, found {len(hits)}: {hits}"
        )
    return hits[0]


def parse_bygb34(path: Path) -> pl.DataFrame:
    """Tidy long table: omraade, opfoerelsesaar, arealtype, anvendelse, year, m2.

    Values are converted from 1,000 m² to m². Raises on any missing/non-numeric cell
    (the download was verified complete; DST's '..'/'-' markers must not appear) and
    validates the parse against the label cross-product.
    """
    years: list[int] | None = None
    omraade = opfoer = arealtype = None
    records: list[tuple[str, str, str, str, int, int]] = []

    with open(path, encoding="iso-8859-1", newline="") as f:
        for rec in csv.reader(f, delimiter=";"):
            cells = [c.strip() for c in rec]
            if not cells or all(not c for c in cells):
                continue
            if years is None:  # skip title lines until the year header row
                if len(cells) > 4 and cells[4].isdigit():
                    years = [int(c) for c in cells[4:]]
                continue
            if len(cells) <= 4 or all(not c for c in cells[4:]):
                # label-only row: sets the carried-forward value for its level
                for level, label in enumerate(cells[:4]):
                    if label:
                        if level == 0:
                            omraade = label
                        elif level == 1:
                            opfoer = label
                        elif level == 2:
                            arealtype = label
                continue
            # data row: (up to) 4 label cells then one value per year
            if cells[1]:
                opfoer = cells[1]
            if cells[2]:
                arealtype = cells[2]
            anvendelse = cells[3]
            values = cells[4:]
            if len(values) != len(years):
                raise ValueError(f"row has {len(values)} values, expected {len(years)}: {rec}")
            for year, v in zip(years, values):
                if not v.lstrip("-").isdigit():
                    raise ValueError(f"non-numeric cell {v!r} ({opfoer}/{arealtype}/{anvendelse}, {year})")
                records.append((omraade, opfoer, arealtype, anvendelse, year, int(v) * 1000))

    if years is None:
        raise ValueError(f"no year header row found in {path}")

    long = pl.DataFrame(
        records,
        schema=["omraade", "opfoerelsesaar", "arealtype", "anvendelse", "year", "m2"],
        orient="row",
    )
    _validate(long, years)
    return long


def _validate(long: pl.DataFrame, years: list[int]) -> None:
    if bad := set(long["omraade"].unique()) - {"Hele landet"}:
        raise ValueError(f"expected national data only, got områder {bad}")
    if set(long["arealtype"].unique()) != _AREALTYPER:
        raise ValueError(f"unexpected arealtyper: {sorted(long['arealtype'].unique())}")
    if years != list(range(years[0], years[-1] + 1)):
        raise ValueError(f"year columns not contiguous: {years}")
    # DST publishes a few dozen small negative cells in the COMPONENT arealtyper
    # (Boligareal/Erhvervsareal; on this download 63 cells, worst −81,000 m² against a
    # ~650M m² national total). They are kept as published so our sums stay identical to
    # DST's own aggregates — but only within tight bounds, and never in the total column.
    neg = long.filter(pl.col("m2") < 0)
    if neg.filter(pl.col("arealtype") == _AT_SAMLET).height:
        raise ValueError("negative cell in Samlet etageareal")
    if neg.height and int(neg["m2"].min()) < -100_000:
        raise ValueError(f"negative stock cell beyond tolerance:\n{neg.sort('m2').head()}")
    # every (opførelsesår, arealtype, anvendelse) combination exactly once per year
    dupes = (
        long.group_by("opfoerelsesaar", "arealtype", "anvendelse", "year")
        .len()
        .filter(pl.col("len") != 1)
    )
    if dupes.height:
        raise ValueError(f"duplicate label combinations:\n{dupes}")
    n_expected = (
        long["opfoerelsesaar"].n_unique() * len(_AREALTYPER) * long["anvendelse"].n_unique() * len(years)
    )
    if long.height != n_expected:
        raise ValueError(f"sparse label grid: {long.height} cells, expected {n_expected}")
    # unit guard: national Samlet etageareal 2018 ≈ 754M m² (verified download, 2026-07-12).
    samlet_2018 = long.filter(
        (pl.col("arealtype") == _AT_SAMLET) & (pl.col("year") == 2018)
    )["m2"].sum()
    if abs(samlet_2018 - 754e6) / 754e6 > 0.05:
        raise ValueError(f"Samlet etageareal 2018 = {samlet_2018:,} m², expected ~754M — unit/parse error?")


def stock_national(long: pl.DataFrame) -> pl.DataFrame:
    """year × national stock (m²) per arealtype + the two denominator columns."""
    wide = (
        long.group_by("year", "arealtype")
        .agg(pl.col("m2").sum())
        .pivot(values="m2", index="year", on="arealtype")
        .sort("year")
    )
    return wide.select(
        "year",
        pl.col(_AT_SAMLET).alias("stock_m2_samlet_etageareal"),
        pl.col(_AT_BOLIG).alias("stock_m2_boligareal"),
        pl.col(_AT_ERHVERV).alias("stock_m2_erhvervsareal"),
        pl.col(_AT_KAELDER).alias("stock_m2_kaelderareal"),
        (pl.col(_AT_BOLIG) + pl.col(_AT_ERHVERV)).alias("stock_m2_bolig_erhverv"),
    )


# --- Numerator (from the indicator registry) ----------------------------------
# Pre-774f90a complete-case area semantics (the manuscript's): last known non-null
# value per building and raw field; etage = byg039 bolig + byg040 erhverv, null only
# when BOTH are null, negative components contribute 0; final areas <= 0 → null
# (negative impossible, zero = "unregistered", not a real 0).


def _attributes() -> pl.LazyFrame:
    """One row per building: complete-case areas (m²) for the two matched pairings."""
    lf = pl.scan_parquet(ind.BYGNING_PATH).sort("virkningFra")

    def last_nonnull(col: str) -> pl.Expr:
        return pl.col(col).drop_nulls().last()

    rolled = (
        lf.group_by("id_lokalId")
        .agg(
            last_nonnull("byg038SamletBygningsareal").alias("area_total"),
            last_nonnull("byg039BygningensSamledeBoligAreal").alias("_bolig"),
            last_nonnull("byg040BygningensSamledeErhvervsAreal").alias("_erhverv"),
        )
        .with_columns(
            pl.when(pl.col("_bolig").is_null() & pl.col("_erhverv").is_null())
            .then(None)
            .otherwise(
                pl.when(pl.col("_bolig") >= 0).then(pl.col("_bolig")).otherwise(0)
                + pl.when(pl.col("_erhverv") >= 0).then(pl.col("_erhverv")).otherwise(0)
            )
            .alias("area_etage"),
        )
        .rename({"id_lokalId": "building_id"})
    )
    return rolled.select(
        "building_id",
        pl.when(pl.col("area_total") > 0).then(pl.col("area_total")).alias("area_total"),
        pl.when(pl.col("area_etage") > 0).then(pl.col("area_etage")).alias("area_etage"),
    )


def numerator() -> tuple[pl.DataFrame, pl.DataFrame]:
    """(annual, coverage) over the full variant grid.

    annual:   variant × year — dated members only: count + complete-case m² sums.
    coverage: variant — share of the FULL membership (dated or not) with a non-null
              value in each numerator area field, matching the old
              ``ablation_summary.csv`` coverage definition.
    """
    attrs = _attributes()
    annuals, coverages = [], []
    for label, demolished in ind.all_variants():
        joined = demolished.join(attrs, on="building_id", how="left")
        coverages.append(
            joined.select(
                pl.lit(label).alias("variant"),
                (pl.col("area_etage").is_not_null().mean() * 100).alias("coverage_pct_etage"),
                (pl.col("area_total").is_not_null().mean() * 100).alias("coverage_pct_total"),
            ).collect()
        )
        out = (
            joined.filter(pl.col("year").is_not_null())
            .group_by("year")
            .agg(
                pl.len().alias("n_buildings"),
                pl.col("area_etage").sum().alias("m2_etage"),
                pl.col("area_total").sum().alias("m2_total"),
            )
            .sort("year")
            .collect()
        )
        annuals.append(out.insert_column(0, pl.Series("variant", [label] * out.height)))
    return pl.concat(annuals), pl.concat(coverages)


# --- Rate computation ---------------------------------------------------------


def annual_rates(annual_df: pl.DataFrame, stock: pl.DataFrame) -> pl.DataFrame:
    """variant × year with both field-matched rates, denominator years only (2011+)."""
    return (
        annual_df.join(stock, on="year", how="inner")  # drops pre-2011 numerator years
        .select(
            "variant",
            "year",
            "n_buildings",
            "m2_etage",
            "stock_m2_bolig_erhverv",
            (pl.col("m2_etage") / pl.col("stock_m2_bolig_erhverv") * 100).alias("rate_etage_pct"),
            "m2_total",
            "stock_m2_samlet_etageareal",
            (pl.col("m2_total") / pl.col("stock_m2_samlet_etageareal") * 100).alias("rate_total_pct"),
        )
        .sort("variant", "year")
    )


def window_summary(rates: pl.DataFrame, coverage_df: pl.DataFrame) -> pl.DataFrame:
    """variant × window: mean of the annual rates (each year over its own 1-Jan stock).

    ``coverage_pct_*`` is the variant-level area coverage over the variant's full
    2000–2025 membership (from ``numerator()``) — the share of demolished
    buildings whose m² the numerator actually sees.
    """
    coverage = coverage_df.select("variant", "coverage_pct_etage", "coverage_pct_total")
    frames = []
    for label, y0, y1, anchor in WINDOWS:
        frames.append(
            rates.filter(pl.col("year").is_between(y0, y1))
            .group_by("variant")
            .agg(
                pl.len().alias("n_years"),
                pl.col("rate_etage_pct").mean().alias("mean_rate_etage_pct"),
                pl.col("rate_total_pct").mean().alias("mean_rate_total_pct"),
                pl.col("m2_etage").mean().alias("mean_m2_etage_per_yr"),
                pl.col("m2_total").mean().alias("mean_m2_total_per_yr"),
            )
            .with_columns(window=pl.lit(label), window_note=pl.lit(anchor))
        )
    return (
        pl.concat(frames)
        .join(coverage, on="variant", how="left")
        .select(
            "window", "window_note", "variant", "n_years",
            "mean_rate_etage_pct", "coverage_pct_etage", "mean_m2_etage_per_yr",
            "mean_rate_total_pct", "coverage_pct_total", "mean_m2_total_per_yr",
        )
        .sort("window", "variant")
    )


def spread(summary: pl.DataFrame) -> pl.DataFrame:
    """The headline reduction: min–max fold spread of the window-mean rate.

    ``scope='base'`` spans D1–D6 (the indicator axis — the paper's headline);
    ``scope='all'`` additionally spans the ``-exdisc`` variants (both axes at once).
    """
    rows = []
    for window in [w[0] for w in WINDOWS]:
        sub = summary.filter(pl.col("window") == window)
        for scope, variants in [
            ("base", BASE_INDICATORS),
            ("all", sub["variant"].unique().to_list()),
        ]:
            s = sub.filter(pl.col("variant").is_in(variants))
            for rate_col, pairing in [
                ("mean_rate_etage_pct", "etage/bolig+erhverv"),
                ("mean_rate_total_pct", "total/samlet_etageareal"),
            ]:
                lo = s.filter(pl.col(rate_col) == s[rate_col].min())
                hi = s.filter(pl.col(rate_col) == s[rate_col].max())
                rows.append(
                    {
                        "window": window,
                        "pairing": pairing,
                        "scope": scope,
                        "min_variant": lo["variant"][0],
                        "min_rate_pct": lo[rate_col][0],
                        "max_variant": hi["variant"][0],
                        "max_rate_pct": hi[rate_col][0],
                        "fold": hi[rate_col][0] / lo[rate_col][0],
                    }
                )
    return pl.DataFrame(rows)


# --- Driver -----------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bygb34", type=Path, default=None, help="BYGB34 csv (default: glob dataset/BYGB34_*.csv)")
    args = ap.parse_args()

    path = args.bygb34 or find_bygb34()
    print(f"Parsing {path.name} …")
    long = parse_bygb34(path)
    stock = stock_national(long)
    stock.write_csv(RESULTS / "stock_national.csv")

    print("Computing numerator from the indicator registry …")
    annual_df, coverage_df = numerator()

    rates = annual_rates(annual_df, stock)
    rates.write_csv(RESULTS / "rates_annual.csv")

    summary = window_summary(rates, coverage_df)
    summary.write_csv(RESULTS / "rates_summary.csv")

    spread_df = spread(summary)
    spread_df.write_csv(RESULTS / "rates_spread.csv")

    print("Rendering figure …")
    plotting.set_style()
    plotting.rate_lines(
        rates,
        "rate_etage_pct",
        "Demolition rate (% of stock floor area / yr)",
        "Annual demolition rate vs stock by indicator",
        FIGURES / "rate_vs_stock",
        BASE_INDICATORS,
        anchors=ANCHORS,
    )

    with pl.Config(tbl_cols=-1, tbl_rows=-1, tbl_width_chars=220):
        print(summary.filter(pl.col("variant").is_in(BASE_INDICATORS)))
        print(spread_df)
    print(f"\nWrote stock_national / rates_annual / rates_summary / rates_spread under {RESULTS}")


if __name__ == "__main__":
    main()
