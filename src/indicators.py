"""Demolition-indicator definitions — self-contained, raw-reading.

Each indicator is one definition of what counts as a demolition in the Danish
BBR register. The article's premise (``docs/indicators.md``) is that these
definitions disagree, so the ablation swaps one for another and measures how the
downstream numbers move. That premise also dictates the *shape* of this file:
the failure mode the article criticises in the KMD extract is **opaque
precompute** — a verdict baked somewhere you cannot audit. So there is no
pre-computed "contract" table here. Every indicator reads the three raw
Datafordeler parquets directly and spells out its whole recipe top-to-bottom;
every research *judgment* (which date means "demolition", partial vs total) lives
visibly inside the indicator it belongs to — and a judgment that applies to *all*
of them is an orthogonal on/off AXIS you compose, not a value baked into one.

An indicator is a function ``() -> pl.LazyFrame`` returning the **set of
demolished buildings** under that definition, one row per building:

    building_id  str    Bygning id_lokalId
    year         int?   the demolition year under THIS indicator (see each below)

Two families, contiguously numbered:

    D1-D3  register-exit signals   (from Bygning: status, forretningsproces)
    D4-D6  demolition-case signals (from Sagsniveau + BBRSag: sagstype, dates)

Membership is row presence; combinations are join algebra
(``D3 = D1 ∩ D2``, ``D5 = D1 ∩ D4``). The discontinued-use-code exclusion is *not*
an indicator but an orthogonal on/off axis (``exclude_discontinued``) composable
with any of them; ``all_variants`` enumerates the full indicator × axis grid. The
shared helpers (``_historical_today``, ``_process3_year``, ``_demolition_cases``)
reduce many rows per building to one, and carry three documented rules that apply
to every indicator using them: D1 counts buildings historical *today*; a
demolition mark on a case's own record of a building counts for that building;
cancelled demolition cases are dropped. ``_status10_year`` (first historical
date, ever) is kept as the shared dating clock for the KMD comparison.

Counts verified against the real data (denominator 6,250,075 IDs, windowed to
2001–2025; checked by ``tests/test_indicators.py`` against an independent
implementation): D1 405,922 · D2 212,238 · D3 180,041 · D4 208,047 (183,966
dated, 24,081 undated: not historical today, case notified 2001–2025) · D5 183,966 · D6 228,045. ``d1_ever``:
411,644. The exclusion axis strips 31–35% from every indicator; under the
earlier definitions, 50.7% of the status-10 buildings it strips *also* had a
formal demolition case (not rechecked), so it is a contested variant, not a
correction.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import polars as pl

# Prefix for every indicator id. Change here to relabel the whole set.
LETTER = "D"

# --- Raw source parquets ----------------------------------------------------
# Full-history Datafordeler grunddata, raw BBR column names, UTC datetimes.
# Overridable (e.g. a driver pointing at a subset) by reassigning before use.
_DATASET = Path(__file__).resolve().parent.parent / "dataset"
BYGNING_PATH = str(_DATASET / "bygning.parquet")
SAGSNIVEAU_PATH = str(_DATASET / "sagsniveau.parquet")
BBRSAG_PATH = str(_DATASET / "bbrsag.parquet")

# Discontinued round-number use-codes (agricultural/industrial categories retired
# in BBR restructurings). The thesis treated a status-10 event on one of these as a
# re-registration artifact rather than a real demolition, reporting >90% fake rates
# on the OLD register generation. On this 2017+ Datafordeler extract that premise
# does not hold: ~34% of EVERY indicator's buildings carry such a code (a base
# rate), and of the status-10 buildings the exclusion would strip, 50.7% ALSO have
# a formal demolition case — i.e. it removes genuine demolitions, not just
# artifacts. So it is exposed as an orthogonal ON/OFF ablation axis
# (`exclude_discontinued`, applicable to ANY indicator), never baked into a single
# "corrected" indicator. Set unchanged from the thesis `remove_outdated`.
DISCONTINUED_CODES = {
    130,
    210,
    220,
    230,
    290,
    310,
    320,
    330,
    390,
    410,
    420,
    430,
    440,
    490,
    520,
    530,
}


# Fixed comparison window, held constant across every indicator so it never
# confounds the indicator choice (docs/indicators.md lists the time window as a
# confound to freeze). Inclusive of both endpoints. Applied as each indicator's
# final step via `_in_window`.
# 2000 is left out: every building in the register on 5 Feb 2000 (the earliest
# effect date, an old conversion date) gets a version starting that day, so
# buildings already historical before then pile up in 2000. 2026 is partial.
YEAR_MIN, YEAR_MAX = 2001, 2025


# --- Mechanical grain-reduction helpers (no research judgment) ---------------
# The raw files are many-rows-per-building (full temporal history). These reduce
# to one row per building. They encode no demolition *decision* — only the
# rollup — so they are safe to share across indicators.


def _in_window(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Clip dated demolitions to ``[YEAR_MIN, YEAR_MAX]``, keeping undated matches.

    Null years are retained on purpose: a building can match an indicator (e.g.
    has a demolition case) yet have no year because it never reached status 10.
    Dropping those would silently collapse D4 into D5 (D1 ∩ D4) and erase it as a
    distinct signal — so undated membership survives; only out-of-window *dated*
    rows are removed.
    """
    return lf.filter(
        pl.col("year").is_between(YEAR_MIN, YEAR_MAX) | pl.col("year").is_null()
    )


def _status10_year() -> pl.LazyFrame:
    """Buildings that ever went ``status == 10`` (Historisk), with demolition year.

    Year = calendar year of the first ``virkningFra`` at status 10 (the register
    effect date of the exit), matching the thesis ``add_demolition_year`` rule.
    """
    return (
        pl.scan_parquet(BYGNING_PATH)
        .filter(pl.col("status") == 10)
        .group_by("id_lokalId")
        .agg(pl.col("virkningFra").min().dt.year().alias("year"))
        .rename({"id_lokalId": "building_id"})
    )


def _historical_today() -> pl.LazyFrame:
    """Buildings whose record is marked historical (``status == 10``) *today*.

    "Today" = the currently valid version (``virkningTil`` is null). Checked on
    this extract: every building has exactly one such version, and it equals the
    last version by effect date. Year = the first status-10 effect date (same
    clock as ``_status10_year``); dating by the start of the latest historical
    stretch instead would change the year for only 1,073 of 445,088 buildings.

    Excludes buildings whose historical mark the register later removed (now
    status 6 again, or 11 "registered by mistake"); ``d1_ever`` keeps them.
    Also excludes a case's own record of a building (2 such records are
    historical today), since those are not buildings.
    """
    current_10 = (
        pl.scan_parquet(BYGNING_PATH)
        .filter(pl.col("virkningTil").is_null() & (pl.col("status") == 10))
        .select(pl.col("id_lokalId").alias("building_id"))
        .unique()
    )
    case_records = _case_record_to_building().select(
        pl.col("sagsdataBygning").alias("building_id")
    )
    return (
        _status10_year()
        .join(current_10, on="building_id", how="semi")
        .join(case_records, on="building_id", how="anti")
    )


def _case_record_to_building() -> pl.LazyFrame:
    """Map a case's own record of a building to the building it belongs to.

    For demolition and rebuilding, a case keeps its own record of the building
    (Sagsniveau ``sagsdataBygning``), separate from the building's own record
    (``stamdataBygning``); for new construction the two are the same ID
    (grunddatamodel, Sagsniveau). Checked: each such case record belongs to
    exactly one building, and none is also used as a building's own record.
    """
    return (
        pl.scan_parquet(SAGSNIVEAU_PATH)
        .filter(
            pl.col("sagsdataBygning").is_not_null()
            & pl.col("stamdataBygning").is_not_null()
            & (pl.col("sagsdataBygning") != pl.col("stamdataBygning"))
        )
        .group_by("sagsdataBygning")
        .agg(pl.col("stamdataBygning").min())
    )


def _process3_year() -> pl.LazyFrame:
    """Buildings with a version marked ``forretningsproces == 3``, on their own
    record or on a case's own record of them.

    Code 3 = "Opdateret grundet nedrivning" (updated due to demolition). In the
    data from the old BBR system (effect dates before 2 June 2017) this mark is
    only on the case's own record of the building, never on the building's own
    record; from June 2017 it is almost always on the building's own record. So
    a case record is mapped to its building (``_case_record_to_building``).

    Year, in this order:
      1. the first code-3 date on the building's own record;
      2. else the first code-3 date on a case record at status 9 ("Afsluttet",
         the case completed);
      3. else the first code-3 date on a case record.
    A case record usually gets a code-3 version when the case is opened
    (status 2, "Projekteret") and another when it is completed (status 9). The
    opening date lies near the notification (median 2 days after). Of the
    91,527 historical buildings dated by a completed case record, the
    completion date is within a day of the historical date for 80.3 %, the
    opening date for 9.8 %. The own-record date is within a day of it for
    99.5 %. 8,813 case-record-only buildings have no completed code-3 version
    and fall back to the first date (4.1 % of D2 in 2001–2025). So
    dating by completion gives D2 the same meaning before and after 2017.
    The last code-3 date was rejected: 3,813 fall on 2017-06-02 (migration).
    """
    p3 = (
        pl.scan_parquet(BYGNING_PATH)
        .filter(pl.col("forretningsproces") == 3)
        .select("id_lokalId", "virkningFra", "status")
    )
    return (
        p3.join(
            _case_record_to_building(),
            left_on="id_lokalId",
            right_on="sagsdataBygning",
            how="left",
        )
        .with_columns(
            pl.col("stamdataBygning").is_not_null().alias("on_case_record"),
            pl.coalesce("stamdataBygning", "id_lokalId").alias("building_id"),
        )
        .group_by("building_id")
        .agg(
            pl.col("virkningFra").filter(~pl.col("on_case_record")).min().alias("own"),
            pl.col("virkningFra")
            .filter(pl.col("on_case_record") & (pl.col("status") == 9))
            .min()
            .alias("case_done"),
            pl.col("virkningFra").filter(pl.col("on_case_record")).min().alias("case_first"),
        )
        .select(
            "building_id",
            pl.coalesce("own", "case_done", "case_first").dt.year().alias("year"),
        )
    )


def _demolition_cases() -> pl.LazyFrame:
    """One row per building linked to a non-cancelled demolition case (31 or 32).

    Join chain: ``Bygning.id_lokalId ◄─stamdataBygning─ Sagsniveau ─byggesag─►
    BBRSag.id_lokalId``. The demolished building is ``stamdataBygning`` (the
    stamobjekt of the case). Rows with a null ``stamdataBygning`` concern only
    part of a building (unit, floor, stairwell) or a technical installation and
    are dropped (16,839 cases, 5.9 % of demolition cases). Cancelled cases
    (``sag007Henlæggelse`` set) are dropped per case.

    Columns:
        building_id        str
        sagstypes_seen     list[int]  distinct {31, 32} seen — NOT collapsed
        case_date_notify   date?      min sag002 Byggesagsdato over the building's
                                       non-cancelled type-32 cases (notification,
                                       ≈ old felt 294); null if it has none
        case_date_complete date?      min sag010 FuldførelseAfByggeri — completion of
                                       CONSTRUCTION (byggeri), NOT a felt-295 analog.
                                       Felt 295 (Gennemført nedrivning) is a Bygning
                                       field and is not distributed; sag010 is a
                                       distinct field. On a demolition case it is only
                                       set when (re)build work is attached, and then
                                       holds that build's completion, not the
                                       demolition's — do NOT use it as a completion date
    """
    cases = (
        pl.scan_parquet(SAGSNIVEAU_PATH)
        .filter(
            # sagstype 31 = Nedrivning delvis, 32 = Nedrivning hel — the only two
            # demolition case types in the BBR kodeliste.
            pl.col("sagstype").is_in([31, 32])
            & pl.col("stamdataBygning").is_not_null()
        )
        .select(["stamdataBygning", "sagstype", "byggesag"])
        .unique()
    )
    # One row per case (BBRSag has several versions per case).
    sag = (
        pl.scan_parquet(BBRSAG_PATH)
        .group_by("id_lokalId")
        .agg(
            pl.col("sag002Byggesagsdato").min(),
            pl.col("sag010FuldførelseAfByggeri").min(),
            # Cancelled ("henlagt") if any version carries a cancellation date.
            # BBR instruks §7.6.11: "En henlæggelse betyder således, at
            # byggesagen annuleres" — the planned work is abandoned. A cancelled
            # case is therefore not evidence of a demolition and is dropped,
            # per case: a building with another, non-cancelled case stays.
            pl.col("sag007Henlæggelse").is_not_null().any().alias("cancelled"),
        )
    )
    return (
        cases.join(sag, left_on="byggesag", right_on="id_lokalId", how="left")
        .filter(~pl.col("cancelled").fill_null(False))
        .group_by("stamdataBygning")
        .agg(
            pl.col("sagstype").unique().sort().alias("sagstypes_seen"),
            # Notification date from total-demolition (32) cases only, so D6's
            # date comes from the same cases that make the building a member.
            pl.col("sag002Byggesagsdato")
            .filter(pl.col("sagstype") == 32)
            .min()
            .alias("case_date_notify"),
            pl.col("sag010FuldførelseAfByggeri").min().alias("case_date_complete"),
        )
        .rename({"stamdataBygning": "building_id"})
    )


# --- Registry ---------------------------------------------------------------


@dataclass(frozen=True)
class Indicator:
    """One demolition definition.

    Attributes:
        id: Registry id, e.g. ``"D1"``.
        name: Short human-readable label.
        description: One-line statement of the rule.
        build: Returns the demolished-building set as ``LazyFrame[building_id, year]``.
    """

    id: str
    name: str
    description: str
    build: Callable[[], pl.LazyFrame]


REGISTRY: dict[str, Indicator] = {}


def indicator(
    num: int,
    name: str,
    description: str,
) -> Callable[[Callable[[], pl.LazyFrame]], Callable[[], pl.LazyFrame]]:
    """Register the decorated function as indicator ``<LETTER><num>``.

    The decorated function takes no arguments and returns the demolished-building
    ``pl.LazyFrame``. It is returned unchanged so it stays directly callable.
    """

    def wrap(fn: Callable[[], pl.LazyFrame]) -> Callable[[], pl.LazyFrame]:
        ind_id = f"{LETTER}{num}"
        if ind_id in REGISTRY:
            raise ValueError(f"Indicator {ind_id!r} already registered")
        REGISTRY[ind_id] = Indicator(
            id=ind_id, name=name, description=description, build=fn
        )
        return fn

    return wrap


# --- D1-D3: register-exit indicators (from Bygning) -------------------------


@indicator(1, "Historical", "status == 10 (Historisk) today")
def d1() -> pl.LazyFrame:
    # Historical *today*: buildings whose historical mark the register later
    # removed are left out (see _historical_today). Still broad: a historical
    # mark can also come from a correction, not a demolition.
    return _in_window(_historical_today())


def d1_ever() -> pl.LazyFrame:
    """Sensitivity variant of D1: ever marked historical, even if later removed.

    NOT an indicator: deliberately unregistered (like ``d4_incl_partial``), so no
    downstream driver sees it. Kept to report what "ever" would give.
    """
    return _in_window(_status10_year())


@indicator(2, "Demolition change", "forretningsproces == 3 (own or case record)")
def d2() -> pl.LazyFrame:
    return _in_window(_process3_year())


@indicator(3, "Historical with demolition change", "D1 and D2")
def d3() -> pl.LazyFrame:
    # Year from D1 (the register-exit date). Window inherited from d1()/d2().
    return d1().join(d2().select("building_id"), on="building_id", how="inner")


# --- D4-D6: demolition-case indicators (from Sagsniveau + BBRSag) ------------


@indicator(4, "Demolition case", "non-cancelled demolition case sagstype == 32 (hel)")
def d4() -> pl.LazyFrame:
    # Year = D1's year (historical today); null for case buildings that are not
    # historical today. D4 has no date of its own, so its dated buildings are
    # exactly D5's; the undated ones are reported separately. An undated
    # building is kept only if its case was notified within the full period
    # (YEAR_MIN..YEAR_MAX), so D4's total covers the same period as the other
    # indicators: this drops cases notified in 2026 (5,406 buildings) and
    # cases with no notification date (5,161).
    cases = _demolition_cases().filter(
        pl.col("sagstypes_seen").list.contains(32)  # 32 = Nedrivning hel (total)
    )
    return _in_window(
        cases.select("building_id", "case_date_notify")
        .join(_historical_today(), on="building_id", how="left")
        .filter(
            pl.col("year").is_not_null()
            | pl.col("case_date_notify").dt.year().is_between(YEAR_MIN, YEAR_MAX)
        )
        .select("building_id", "year")
    )


def d4_incl_partial() -> pl.LazyFrame:
    """Sensitivity variant of D4 that also admits partial-demolition cases.

    NOT an indicator: deliberately unregistered, so ``all_indicators()`` /
    ``all_variants()`` and every downstream driver never see it. Kept only as a
    code-level sensitivity check on the sagstype-31 axis (admitting partials
    changes D4 by ~5% of buildings, Jaccard 0.95, and the 2018–2025 annual rate
    by <0.5%). Collapse-free: only ~2.7% of case-linked buildings carry both 31
    and 32, and the raw `sagstypes_seen` list handles them with zero judgment —
    no "prefer 32" rule.
    """
    cases = _demolition_cases().filter(
        # 31 = Nedrivning delvis (partial), 32 = Nedrivning hel (total).
        pl.col("sagstypes_seen").list.contains(31)
        | pl.col("sagstypes_seen").list.contains(32)
    )
    return _in_window(
        cases.select("building_id").join(
            _historical_today(), on="building_id", how="left"
        )
    )


@indicator(5, "Historical with demolition case", "D1 and D4")
def d5() -> pl.LazyFrame:
    # Year from D1 (register-exit = the closest completion timestamp we have).
    # Window inherited from d1().
    return d1().join(d4().select("building_id"), on="building_id", how="inner")


@indicator(
    6,
    "Demolition case, dated by notification",
    "non-cancelled total-demolition case with a notification date (sag002)",
)
def d6() -> pl.LazyFrame:
    """A case *date* stands in for felt 295 "Gennemført nedrivning".

    Felt 295 (the real completion flag) is a ``Bygning`` attribute and is NOT
    distributed on Datafordeler, so it cannot be reconstructed from this feed. We
    date demolitions by ``case_date_notify`` (sag002 Byggesagsdato ≈ old felt 294
    notification): the grunddatamodel defines sag002 as case-type-dependent (the
    demolition date for a demolition case), it is well populated and
    semantically clean. ``case_date_complete`` (sag010) is NOT a usable fallback —
    it is *fuldførelse af byggeri* (construction completion), a distinct field from
    felt 295, so on a demolition case it carries the attached (re)build's completion
    date, not the demolition's; using it would date demolitions by when construction
    finished.

    This counts total-demolition cases (sagstype 32, like D4) dated by
    notification — it must not be read as a confirmed completed demolition.
    """
    return _in_window(
        _demolition_cases()
        .filter(
            # 32 = Nedrivning hel (total); same membership rule as D4.
            pl.col("sagstypes_seen").list.contains(32)
            & pl.col("case_date_notify").is_not_null()
        )
        .select(
            "building_id",
            pl.col("case_date_notify").dt.year().alias("year"),
        )
    )


# --- Discontinued-code exclusion (orthogonal on/off axis) -------------------


# Suffix marking the discontinued-exclusion axis = ON, e.g. ``"D1-exdisc"``.
EXCL_SUFFIX = "-exdisc"


def exclude_discontinued(demolished: pl.LazyFrame) -> pl.LazyFrame:
    """Drop buildings that ever carried a ``DISCONTINUED_CODES`` use-code.

    The on/off axis, applicable to ANY indicator's output — ``exclude_discontinued
    (d1())`` reproduces the historical "corrected historical" indicator. Note (see
    ``DISCONTINUED_CODES``): on this extract it strips ~34% everywhere and half the
    status-10 buildings it removes have a formal demolition case, so it
    over-corrects — run it as a contested variant and score it against BOSSINF,
    never as ground-truth cleanup.
    """
    artifacts = (
        pl.scan_parquet(BYGNING_PATH)
        .filter(pl.col("byg021BygningensAnvendelse").is_in(list(DISCONTINUED_CODES)))
        .select(pl.col("id_lokalId").alias("building_id"))
        .unique()
    )
    return demolished.join(artifacts, on="building_id", how="anti")


# --- Accessors --------------------------------------------------------------


def get(indicator_id: str) -> Indicator:
    """Return the indicator with the given id (e.g. ``"D1"``)."""
    return REGISTRY[indicator_id]


def all_indicators() -> list[Indicator]:
    """Return every registered indicator, ordered by id."""
    return [REGISTRY[k] for k in sorted(REGISTRY, key=lambda i: int(i[len(LETTER) :]))]


def all_variants() -> list[tuple[str, pl.LazyFrame]]:
    """Full ablation grid: every indicator × {discontinued-exclusion off, on}.

    Yields ``(label, LazyFrame)`` pairs — ``"D1"`` (axis off) and ``"D1-exdisc"``
    (axis on) — so a driver can iterate the whole grid uniformly.
    """
    variants: list[tuple[str, pl.LazyFrame]] = []
    for ind in all_indicators():
        variants.append((ind.id, ind.build()))
        variants.append((f"{ind.id}{EXCL_SUFFIX}", exclude_discontinued(ind.build())))
    return variants
