# Shared analysis filters and conventions

This document records the rules that should be applied consistently in the
demolition-indicator pipeline. It does not require another intermediate
Parquet file. The analysis can read the cleaned temporal files directly.

The central principle is:

> Change the demolition indicator while holding all other filters and
> reporting rules fixed.

## Order of operations

Apply the steps in this order for every indicator:

1. Read the relevant complete temporal Parquet file.
2. Detect candidate demolition events using the indicator definition.
3. Collapse temporal versions to at most one candidate event per building for
   that indicator.
4. Attach the building attributes required for counts and breakdowns.
5. Apply the shared total-area quality filter described below.
6. Apply the same agreed analysis period to every indicator.
7. Calculate counts, area coverage and square metres.

The area filter must be applied after candidate-event detection. Applying it
beforehand could remove rows used by one indicator more often than rows used by
another indicator and thereby change the indicator definition itself.

## One area measure

The study uses only:

```text
byg038SamletBygningsareal
```

This is BBR's total floor area. Do not fill it from building footprint,
residential area, commercial area or a hybrid definition.

## Required negative-area filter

Candidate records with negative total floor area are excluded using the same
rule for every indicator.

Null and zero are deliberately retained:

- null means that no total floor area is available;
- zero is a recorded value and is useful for diagnosing data quality;
- neither contributes positive square metres;
- both remain relevant for demolition counts and coverage reporting.

In Polars, the filter must explicitly retain nulls:

```python
area = pl.col("byg038SamletBygningsareal")
filtered = candidates.filter(area.is_null() | (area >= 0))
```

Using only `area >= 0` would also discard null values because a comparison with
null does not evaluate to true.

Record the number removed by the negative-area filter for every indicator.

## Building-use treatment

Keep all building-use groups in the main candidate data, including
`Outbuildings & other`.

Codes 910-930 cannot normally contain total floor area in BBR. The wider
`Outbuildings & other` group is therefore expected to have very high area
missingness. This is a coverage finding, not a reason to remove the buildings
from demolition counts.

Retain missing use codes as an explicit `Unknown` category in summaries rather
than silently dropping them.

## Discontinued use codes

Do not remove discontinued use codes from the main inclusive results. Their
unusual behaviour is part of the study.

The discontinued-code list currently used is:

```text
130, 210, 220, 230, 290, 310, 320, 330,
390, 410, 420, 430, 440, 490, 520, 530
```

If a filtered sensitivity result is produced, apply the same discontinued-code
filter to every indicator and label the result clearly. Also report the
excluded candidates as an ambiguous category.

## Construction year

Do not filter on construction year for the current counts and square-metre
analysis. Missing or unusual construction year does not prove that a building
or demolition-related register event is invalid.

Construction-year rules can be added later if the study introduces age,
lifespan or construction-period results.

## Repeated temporal records

Do not interpret multiple matching temporal rows as multiple demolitions.
Each indicator must define a deterministic collapse rule that gives at most one
candidate event per `id_lokalId`.

The usual starting rule is the earliest `virkningFra` satisfying that
indicator. Keep `registreringFra` as well so retrospective registrations and
timing differences can be audited.

The extract contains buildings that have more than one status-10 temporal
version, so checking uniqueness after collapse is required.

## Reactivated buildings

Buildings with a non-status-10 observation after a status-10 observation are
ambiguous, not certainly erroneous. Keep them in the inclusive results and
flag them.

If a strict result excludes reactivated buildings, apply the same building-ID
exclusion to every indicator and report how many candidates are removed.

## Analysis period

Every indicator must use the same time window. The current extract starts its
Datafordeler registration history in June 2017 and extends into incomplete
2026.

For full-calendar-year comparisons, the recommended initial window is:

```text
2018-2025
```

The team should confirm this window before final results are produced. If 2017
or 2026 is shown, label it as partial coverage rather than comparing it directly
with complete years.

## Required output for every indicator

For each indicator and reporting group, retain enough information to reconcile
the result:

```text
candidate_building_count_before_area_filter
negative_area_buildings_excluded
candidate_building_count_after_area_filter
buildings_with_non_null_area
buildings_with_positive_area
buildings_with_zero_area
buildings_with_missing_area
area_coverage_pct
total_area_m2
```

Suggested coverage definition:

```text
area_coverage_pct =
    buildings_with_non_null_area
    / candidate_building_count_after_area_filter
    * 100
```

Zero-area records count as non-null coverage but contribute zero square metres.
Also report `positive_area_coverage_pct` separately.

## Validation checks

The analysis should fail or warn when any of these conditions is violated:

- duplicate `(indicator, id_lokalId)` pairs remain after event collapse;
- a negative `byg038SamletBygningsareal` remains after the shared filter;
- candidate count after filtering does not equal the sum of positive, zero and
  missing-area buildings;
- different indicators use different time windows;
- an optional discontinued-code or reactivation filter is applied to only some
  indicators;
- null areas disappear because of an accidental `area >= 0` filter;
- outbuildings disappear from candidate counts without an explicit analysis
  decision.

## Current decisions summary

| Decision | Rule |
| --- | --- |
| Area measure | `byg038SamletBygningsareal` only |
| Negative total area | Exclude after indicator detection |
| Null total area | Keep for counts and report as missing |
| Zero total area | Keep for counts and report separately |
| Outbuildings | Keep in the candidate data |
| Missing use code | Keep as `Unknown` |
| Discontinued codes | Keep in inclusive results; optional shared sensitivity filter |
| Construction year | No filter for current analysis |
| Multiple temporal matches | Collapse to one event per building and indicator |
| Reactivation after status 10 | Flag; optional shared strict sensitivity filter |
| Area substitution | None |

These conventions should be implemented once in shared helper functions rather
than copied into each indicator implementation.
