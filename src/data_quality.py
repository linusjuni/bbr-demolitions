"""Generate reproducible quality statistics for the cleaned temporal BBR data."""

from __future__ import annotations

import argparse
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import polars as pl


@dataclass(frozen=True)
class AreaField:
    column: str
    label: str
    role: str


AREA_FIELDS = (
    AreaField("byg038SamletBygningsareal", "Total floor area", "primary candidate"),
    AreaField("byg039BygningensSamledeBoligAreal", "Residential area", "use component"),
    AreaField("byg040BygningensSamledeErhvervsAreal", "Commercial area", "use component"),
    AreaField("byg041BebyggetAreal", "Building footprint", "diagnostic only"),
    AreaField("byg042ArealIndbyggetGarage", "Integrated garage", "supplementary"),
    AreaField("byg043ArealIndbyggetCarport", "Integrated carport", "supplementary"),
    AreaField("byg044ArealIndbyggetUdhus", "Integrated outbuilding", "supplementary"),
    AreaField("byg045ArealIndbyggetUdestueEllerLign", "Integrated conservatory", "supplementary"),
    AreaField(
        "byg046SamletArealAfLukkedeOverdækningerPåBygningen",
        "Closed covered area",
        "supplementary",
    ),
    AreaField(
        "byg047ArealAfAffaldsrumITerrænniveau",
        "Ground-level waste room",
        "supplementary",
    ),
    AreaField("byg048AndetAreal", "Other area", "use component"),
    AreaField("byg049ArealAfOverdækketAreal", "Covered area", "supplementary"),
    AreaField(
        "byg050ArealÅbneOverdækningerPåBygningenSamlet",
        "Open covered area",
        "supplementary",
    ),
    AreaField("byg051Adgangsareal", "Access area", "supplementary"),
    AreaField(
        "byg130ArealAfUdvendigEfterisolering",
        "External insulation area",
        "supplementary",
    ),
)

PRINCIPAL_AREA_COLUMNS = tuple(field.column for field in AREA_FIELDS[:4])

CRITICAL_COLUMNS = {
    "bygning": (
        "id_lokalId",
        "status",
        "forretningsproces",
        "registreringFra",
        "virkningFra",
        "kommunekode",
        "region_name",
        "byg021BygningensAnvendelse",
        "building_use_group",
        "byg026Opførelsesår",
        *PRINCIPAL_AREA_COLUMNS,
    ),
    "bbrsag": (
        "id_lokalId",
        "status",
        "forretningsproces",
        "registreringFra",
        "virkningFra",
        "kommunekode",
        "region_name",
        "sag002Byggesagsdato",
        "sag010FuldførelseAfByggeri",
        "sag012Byggesagskode",
        "sag008FærdigtBygningsareal",
    ),
    "sagsniveau": (
        "id_lokalId",
        "status",
        "forretningsproces",
        "registreringFra",
        "virkningFra",
        "kommunekode",
        "region_name",
        "niveautype",
        "sagstype",
        "byggesag",
        "stamdataBygning",
        "sagsdataBygning",
    ),
}

REPORT_CRITICAL_COLUMNS = {
    "bygning": {
        "forretningsproces": "Business process",
        "byg021BygningensAnvendelse": "Building-use code",
        "byg026Opførelsesår": "Construction year",
    },
    "bbrsag": {
        "sag002Byggesagsdato": "Case date",
        "sag010FuldførelseAfByggeri": "Completion date",
        "sag012Byggesagskode": "Case code",
        "sag008FærdigtBygningsareal": "Completed building area",
    },
    "sagsniveau": {
        "sagstype": "Case type",
        "byggesag": "BBRSag reference",
        "stamdataBygning": "Master-building reference",
        "sagsdataBygning": "Case-building reference",
    },
}


def currently_effective(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Return rows whose registration and effect intervals are both open-ended."""
    return lf.filter(
        pl.col("registreringTil").is_null() & pl.col("virkningTil").is_null()
    )


def _require_columns(lf: pl.LazyFrame, columns: Iterable[str], entity: str) -> None:
    available = set(lf.collect_schema().names())
    missing = sorted(set(columns) - available)
    if missing:
        raise ValueError(f"{entity} is missing required quality columns: {missing}")


def summarize_dataset(entity: str, lf: pl.LazyFrame) -> pl.DataFrame:
    """Summarize entity size, time coverage, and temporal versions per ID."""
    _require_columns(
        lf,
        (
            "id_lokalId",
            "registreringFra",
            "registreringTil",
            "virkningFra",
            "virkningTil",
        ),
        entity,
    )
    is_current = pl.col("registreringTil").is_null() & pl.col("virkningTil").is_null()
    overview = lf.select(
        pl.len().alias("temporal_rows"),
        pl.col("id_lokalId").n_unique().alias("unique_ids"),
        pl.col("id_lokalId").is_null().sum().alias("null_ids"),
        is_current.sum().alias("currently_effective_rows"),
        pl.col("id_lokalId")
        .filter(is_current)
        .n_unique()
        .alias("currently_effective_unique_ids"),
        pl.col("registreringFra").min().alias("registration_start"),
        pl.col("registreringFra").max().alias("registration_end"),
        pl.col("virkningFra").min().alias("effect_start"),
        pl.col("virkningFra").max().alias("effect_end"),
    ).collect()

    versions = lf.group_by("id_lokalId").agg(pl.len().alias("versions"))
    version_stats = versions.select(
        pl.col("versions").mean().alias("versions_mean"),
        pl.col("versions").median().alias("versions_median"),
        pl.col("versions").quantile(0.95).alias("versions_p95"),
        pl.col("versions").max().alias("versions_max"),
    ).collect()

    return (
        pl.concat([overview, version_stats], how="horizontal_extend")
        .with_columns(
            pl.lit(entity).alias("entity"),
            pl.lit(len(lf.collect_schema())).alias("column_count"),
            (
                pl.col("unique_ids") - pl.col("currently_effective_unique_ids")
            ).alias("ids_without_currently_effective_row"),
            (
                pl.col("currently_effective_rows")
                - pl.col("currently_effective_unique_ids")
            ).alias("duplicate_currently_effective_rows"),
        )
        .select("entity", "column_count", pl.exclude("entity", "column_count"))
    )


def _missing_expression(column: str, dtype: pl.DataType) -> pl.Expr:
    missing = pl.col(column).is_null()
    if dtype == pl.String:
        missing = missing | (pl.col(column).str.strip_chars() == "")
    if dtype.is_float():
        missing = missing | pl.col(column).is_nan()
    return missing


def summarize_missingness(
    entity: str,
    scope_name: str,
    lf: pl.LazyFrame,
    columns: Iterable[str],
) -> pl.DataFrame:
    """Return null/NaN/blank and zero counts for selected columns in one scan."""
    requested = tuple(columns)
    _require_columns(lf, requested, entity)
    schema = lf.collect_schema()
    expressions: list[pl.Expr] = [pl.len().alias("__rows")]

    for column in requested:
        dtype = schema[column]
        expressions.append(
            _missing_expression(column, dtype).sum().alias(f"{column}__missing")
        )
        if dtype.is_numeric():
            expressions.append((pl.col(column) == 0).sum().alias(f"{column}__zero"))
        if dtype.is_float():
            expressions.append(pl.col(column).is_nan().sum().alias(f"{column}__nan"))

    values = lf.select(expressions).collect().row(0, named=True)
    row_count = values["__rows"]
    rows = []
    for column in requested:
        dtype = schema[column]
        missing_count = values[f"{column}__missing"]
        rows.append(
            {
                "entity": entity,
                "scope": scope_name,
                "column": column,
                "dtype": str(dtype),
                "row_count": row_count,
                "missing_count": missing_count,
                "missing_pct": _percentage(missing_count, row_count),
                "nan_count": values.get(f"{column}__nan", 0),
                "zero_count": values.get(f"{column}__zero"),
            }
        )
    return pl.DataFrame(rows)


def summarize_area_fields(
    scope_name: str, lf: pl.LazyFrame, fields: tuple[AreaField, ...] = AREA_FIELDS
) -> pl.DataFrame:
    """Summarize coverage and distributions for every true Bygning area field."""
    columns = tuple(field.column for field in fields)
    _require_columns(lf, columns, "bygning")
    expressions: list[pl.Expr] = [pl.len().alias("__rows")]
    for field in fields:
        column = pl.col(field.column)
        expressions.extend(
            (
                column.is_null().sum().alias(f"{field.column}__null"),
                (column == 0).sum().alias(f"{field.column}__zero"),
                (column < 0).sum().alias(f"{field.column}__negative"),
                (column > 0).sum().alias(f"{field.column}__positive"),
                column.min().alias(f"{field.column}__min"),
                column.mean().alias(f"{field.column}__mean"),
                column.median().alias(f"{field.column}__median"),
                column.quantile(0.95).alias(f"{field.column}__p95"),
                column.quantile(0.99).alias(f"{field.column}__p99"),
                column.max().alias(f"{field.column}__max"),
                column.sum().alias(f"{field.column}__sum"),
            )
        )

    values = lf.select(expressions).collect().row(0, named=True)
    row_count = values["__rows"]
    rows = []
    for field in fields:
        prefix = field.column
        null_count = values[f"{prefix}__null"]
        rows.append(
            {
                "scope": scope_name,
                "column": field.column,
                "label": field.label,
                "role": field.role,
                "row_count": row_count,
                "null_count": null_count,
                "null_pct": _percentage(null_count, row_count),
                "zero_count": values[f"{prefix}__zero"],
                "negative_count": values[f"{prefix}__negative"],
                "nonpositive_count": values[f"{prefix}__zero"]
                + values[f"{prefix}__negative"],
                "unusable_count": null_count
                + values[f"{prefix}__zero"]
                + values[f"{prefix}__negative"],
                "unusable_pct": _percentage(
                    null_count
                    + values[f"{prefix}__zero"]
                    + values[f"{prefix}__negative"],
                    row_count,
                ),
                "positive_count": values[f"{prefix}__positive"],
                "min_m2": values[f"{prefix}__min"],
                "mean_m2": values[f"{prefix}__mean"],
                "median_m2": values[f"{prefix}__median"],
                "p95_m2": values[f"{prefix}__p95"],
                "p99_m2": values[f"{prefix}__p99"],
                "max_m2": values[f"{prefix}__max"],
                "sum_m2": values[f"{prefix}__sum"],
            }
        )
    return pl.DataFrame(rows)


def summarize_area_by_use(lf: pl.LazyFrame, scope_name: str) -> pl.DataFrame:
    """Show whether area coverage differs systematically between use groups."""
    columns = ("building_use_group", *PRINCIPAL_AREA_COLUMNS)
    _require_columns(lf, columns, "bygning")
    expressions: list[pl.Expr] = [pl.len().alias("__rows")]
    for column in PRINCIPAL_AREA_COLUMNS:
        expressions.extend(
            (
                pl.col(column).is_null().sum().alias(f"{column}__null"),
                (pl.col(column) == 0).sum().alias(f"{column}__zero"),
                pl.col(column).sum().alias(f"{column}__sum"),
            )
        )
    grouped = lf.group_by("building_use_group").agg(expressions).collect()
    labels = {field.column: field.label for field in AREA_FIELDS}
    rows = []
    for record in grouped.iter_rows(named=True):
        row_count = record["__rows"]
        for column in PRINCIPAL_AREA_COLUMNS:
            null_count = record[f"{column}__null"]
            rows.append(
                {
                    "scope": scope_name,
                    "building_use_group": record["building_use_group"],
                    "column": column,
                    "label": labels[column],
                    "row_count": row_count,
                    "null_count": null_count,
                    "null_pct": _percentage(null_count, row_count),
                    "zero_count": record[f"{column}__zero"],
                    "sum_m2": record[f"{column}__sum"],
                }
            )
    return pl.DataFrame(rows).sort(
        "scope", "building_use_group", "column", nulls_last=True
    )


def summarize_area_consistency(lf: pl.LazyFrame, scope_name: str) -> pl.DataFrame:
    """Compare the principal area concepts without treating them as substitutes."""
    total = pl.col("byg038SamletBygningsareal")
    residential = pl.col("byg039BygningensSamledeBoligAreal")
    commercial = pl.col("byg040BygningensSamledeErhvervsAreal")
    footprint = pl.col("byg041BebyggetAreal")
    other = pl.col("byg048AndetAreal")
    required = (
        "byg038SamletBygningsareal",
        "byg039BygningensSamledeBoligAreal",
        "byg040BygningensSamledeErhvervsAreal",
        "byg041BebyggetAreal",
        "byg048AndetAreal",
    )
    _require_columns(lf, required, "bygning")

    total_present = total.is_not_null()
    footprint_present = footprint.is_not_null()
    both_positive = (total > 0) & (footprint > 0)
    ratio = total.cast(pl.Float64) / footprint
    result = lf.select(
        pl.len().alias("rows"),
        (total_present & footprint_present).sum().alias("both_present"),
        (total_present & ~footprint_present).sum().alias("total_only"),
        (~total_present & footprint_present).sum().alias("footprint_only"),
        (~total_present & ~footprint_present).sum().alias("neither_present"),
        total_present.sum().alias("total_present"),
        (
            total_present
            & (total == residential.fill_null(0) + commercial.fill_null(0))
        )
        .sum()
        .alias("total_equals_residential_plus_commercial"),
        (
            total_present
            & (
                total
                == residential.fill_null(0)
                + commercial.fill_null(0)
                + other.fill_null(0)
            )
        )
        .sum()
        .alias("total_equals_residential_commercial_other"),
        both_positive.sum().alias("both_positive"),
        ratio.filter(both_positive).median().alias("floor_to_footprint_ratio_median"),
        ratio.filter(both_positive)
        .quantile(0.95)
        .alias("floor_to_footprint_ratio_p95"),
    ).collect().row(0, named=True)

    definitions = (
        (
            "both_present",
            result["both_present"],
            result["rows"],
            "Both total floor area and footprint are recorded.",
        ),
        (
            "total_only",
            result["total_only"],
            result["rows"],
            "Total floor area is recorded but footprint is missing.",
        ),
        (
            "footprint_only",
            result["footprint_only"],
            result["rows"],
            "Footprint is recorded but total floor area is missing.",
        ),
        (
            "neither_present",
            result["neither_present"],
            result["rows"],
            "Both principal area measures are missing.",
        ),
        (
            "total_equals_residential_plus_commercial",
            result["total_equals_residential_plus_commercial"],
            result["total_present"],
            "Missing component values are treated as zero for this check.",
        ),
        (
            "total_equals_residential_commercial_other",
            result["total_equals_residential_commercial_other"],
            result["total_present"],
            "Missing component values are treated as zero for this check.",
        ),
        (
            "floor_to_footprint_ratio_median",
            result["floor_to_footprint_ratio_median"],
            result["both_positive"],
            "Median ratio among rows where both measures are positive.",
        ),
        (
            "floor_to_footprint_ratio_p95",
            result["floor_to_footprint_ratio_p95"],
            result["both_positive"],
            "95th percentile ratio among rows where both measures are positive.",
        ),
    )
    return pl.DataFrame(
        [
            {
                "scope": scope_name,
                "metric": metric,
                "value": value,
                "denominator": denominator,
                "pct_of_denominator": _percentage(value, denominator)
                if metric not in {
                    "floor_to_footprint_ratio_median",
                    "floor_to_footprint_ratio_p95",
                }
                else None,
                "note": note,
            }
            for metric, value, denominator, note in definitions
        ]
    )


def _percentage(numerator: int | float | None, denominator: int | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return 100.0 * numerator / denominator


def _write_area_plot(area_stats: pl.DataFrame, output_path: Path) -> None:
    os.environ.setdefault(
        "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "bbr-matplotlib")
    )
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    scopes = ("currently_effective", "currently_effective_status_10")
    plot_data = area_stats.filter(pl.col("scope").is_in(scopes))
    labels = [field.label for field in AREA_FIELDS]
    y_positions = list(range(len(labels)))

    fig, ax = plt.subplots(figsize=(10, 8))
    colors = {
        "currently_effective": "#247BA0",
        "currently_effective_status_10": "#D1495B",
    }
    display_names = {
        "currently_effective": "All currently effective buildings",
        "currently_effective_status_10": "Currently effective status 10",
    }
    for offset, scope in ((-0.18, scopes[0]), (0.18, scopes[1])):
        values_by_label = {
            row["label"]: row["null_pct"]
            for row in plot_data.filter(pl.col("scope") == scope).iter_rows(named=True)
        }
        values = [values_by_label[label] for label in labels]
        ax.barh(
            [position + offset for position in y_positions],
            values,
            height=0.34,
            color=colors[scope],
            label=display_names[scope],
        )

    ax.set_yticks(y_positions, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Missing values (%)")
    ax.set_title("Coverage of BBR building-area fields", pad=42)
    ax.grid(axis="x", color="#D9D9D9", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.01),
        ncol=2,
        frameon=False,
    )
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _format_int(value: int | float | None) -> str:
    if value is None:
        return "n/a"
    return f"{int(value):,}"


def _format_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}%"


def _markdown_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join((header, separator, *body))


def render_report(
    dataset_summary: pl.DataFrame,
    critical_missingness: pl.DataFrame,
    area_stats: pl.DataFrame,
    area_by_use: pl.DataFrame,
    output_path: Path,
) -> None:
    """Render the main findings and interpretation as a readable Markdown report."""
    overview_rows = []
    for row in dataset_summary.iter_rows(named=True):
        overview_rows.append(
            (
                row["entity"],
                _format_int(row["temporal_rows"]),
                _format_int(row["unique_ids"]),
                _format_int(row["currently_effective_rows"]),
                _format_int(row["ids_without_currently_effective_row"]),
                f"{row['versions_mean']:.2f}",
                _format_int(row["versions_max"]),
            )
        )

    critical_rows = []
    for entity, columns in REPORT_CRITICAL_COLUMNS.items():
        for column, label in columns.items():
            row = critical_missingness.filter(
                (pl.col("entity") == entity)
                & (pl.col("scope") == "currently_effective")
                & (pl.col("column") == column)
            ).row(0, named=True)
            critical_rows.append(
                (
                    entity,
                    f"`{column}`",
                    label,
                    _format_int(row["missing_count"]),
                    _format_pct(row["missing_pct"]),
                )
            )

    area_rows = []
    for field in AREA_FIELDS[:4]:
        current = area_stats.filter(
            (pl.col("scope") == "currently_effective")
            & (pl.col("column") == field.column)
        ).row(0, named=True)
        historical = area_stats.filter(
            (pl.col("scope") == "currently_effective_status_10")
            & (pl.col("column") == field.column)
        ).row(0, named=True)
        area_rows.append(
            (
                f"`{field.column}`",
                field.label,
                _format_pct(current["null_pct"]),
                _format_pct(historical["null_pct"]),
                _format_int(historical["nonpositive_count"]),
                _format_int(current["median_m2"]),
                _format_int(current["p95_m2"]),
            )
        )

    anomaly_rows = []
    for field in AREA_FIELDS[:4]:
        current = area_stats.filter(
            (pl.col("scope") == "currently_effective")
            & (pl.col("column") == field.column)
        ).row(0, named=True)
        historical = area_stats.filter(
            (pl.col("scope") == "currently_effective_status_10")
            & (pl.col("column") == field.column)
        ).row(0, named=True)
        anomaly_rows.append(
            (
                field.label,
                _format_int(current["zero_count"]),
                _format_int(current["negative_count"]),
                _format_int(historical["zero_count"]),
                _format_int(historical["negative_count"]),
            )
        )

    total_by_use = area_by_use.filter(
        (pl.col("scope") == "currently_effective")
        & (pl.col("column") == "byg038SamletBygningsareal")
    ).sort("null_pct", descending=True)
    use_rows = [
        (
            row["building_use_group"] or "Missing use group",
            _format_int(row["row_count"]),
            _format_pct(row["null_pct"]),
        )
        for row in total_by_use.iter_rows(named=True)
    ]

    status_10_total_by_use = area_by_use.filter(
        (pl.col("scope") == "currently_effective_status_10")
        & (pl.col("column") == "byg038SamletBygningsareal")
        & (
            pl.col("building_use_group").is_null()
            | (pl.col("building_use_group") != "Outbuildings & other")
        )
    )
    status_10_non_outbuilding_rows = status_10_total_by_use["row_count"].sum()
    status_10_non_outbuilding_nulls = status_10_total_by_use["null_count"].sum()
    status_10_non_outbuilding_zeros = status_10_total_by_use["zero_count"].sum()
    non_outbuilding_missing_pct = _percentage(
        status_10_non_outbuilding_nulls,
        status_10_non_outbuilding_rows,
    )
    non_outbuilding_summary = (
        f"Among {_format_int(status_10_non_outbuilding_rows)} currently effective "
        "status-10 buildings outside `Outbuildings & other`, only "
        f"{_format_int(status_10_non_outbuilding_nulls)} "
        f"({_format_pct(non_outbuilding_missing_pct)}) "
        "lack total floor area. A further "
        f"{_format_int(status_10_non_outbuilding_zeros)} have a recorded value of zero."
    )

    overview_table = _markdown_table(
        (
            "Dataset",
            "Temporal rows",
            "Unique IDs",
            "Currently effective rows",
            "IDs without current row",
            "Mean versions/ID",
            "Maximum versions",
        ),
        overview_rows,
    )
    critical_table = _markdown_table(
        ("Dataset", "Column", "Meaning", "Missing", "Missing share"),
        critical_rows,
    )
    principal_area_table = _markdown_table(
        (
            "Column",
            "Meaning",
            "Missing: all current",
            "Missing: status 10",
            "Non-positive: status 10",
            "Median non-null m2",
            "95th percentile m2",
        ),
        area_rows,
    )
    anomaly_table = _markdown_table(
        (
            "Area concept",
            "Zero: all current",
            "Negative: all current",
            "Zero: status 10",
            "Negative: status 10",
        ),
        anomaly_rows,
    )

    report = f"""# BBR data-quality assessment

This report is generated from the cleaned temporal Parquet files by
`src/data_quality.py`. It describes data coverage; it does not apply or select a
demolition indicator.

Run it again with:

```bash
.venv/bin/python -m src.data_quality
```

## Dataset overview

{overview_table}

A *currently effective row* has both `registreringTil` and `virkningTil`
missing. No ID has more than one such row in this extract. A small number of
`Bygning` and `BBRSag` IDs and a larger group of `Sagsniveau` IDs have no
currently effective row, which is reported separately above. Statistics at
this scope avoid giving extra weight to objects with many historical versions.

## Coverage of analysis-critical fields

{critical_table}

The full CSV reports all selected critical fields for both temporal rows and
currently effective rows. High missingness is not automatically an error. For
example, the two `Sagsniveau` building-reference fields are populated only for
records that concern a building, and completed building area in `BBRSag` is an
optional case attribute. These numbers describe the usable coverage for later
joins and indicators; they do not justify filling missing values.

## Principal building-area fields

{principal_area_table}

![Missingness of building-area fields](../results/figures/data_quality_area_missingness.png)

Status 10 is included here as one practically relevant quality-check subset,
not as a preferred demolition indicator. The analysis applies the selected
area rule identically to every candidate indicator.

BBR defines `byg038SamletBygningsareal` as the sum of floor areas, excluding
basement and attic area. It cannot be entered for small buildings with use
codes 910-930. BBR defines `byg041BebyggetAreal` as the footprint occupied by
the building when viewed from above. The measures are therefore not
interchangeable even when both are present.

### Study decision

This study uses `byg038SamletBygningsareal` as its only demolished-area
measure, consistent with the area concept used in the comparison literature.
The other area columns remain in this quality audit as context but are not
alternative outcome definitions in the analysis. Missing total floor area is
not filled from footprint or any other field.

Buildings with null or zero total floor area remain relevant for demolition
counts and for documenting coverage, including the concentration of missing
values among outbuildings. Rows with negative total floor area are excluded by
the analysis pipeline using the same rule for every demolition indicator. The
canonical cleaned data retains the original values.

All area-measurement columns are stored as nullable integers, so they cannot
contain floating-point `NaN`; their missing values are represented by nulls.
Zero and negative values are counted separately because they are present values
but cannot represent a positive demolished area.

### Non-positive area values

{anomaly_table}

Negative principal areas occur in currently effective non-status-10 records but
not in the currently effective status-10 subset. Under the study decision,
negative `byg038SamletBygningsareal` records are filtered consistently for all
indicators. Negative values in the other fields remain a diagnostic finding.
Zero total floor area is retained and reported because it provides no square
metres despite being non-null.

Official definitions:

- [BBR: samlet bygningsareal](https://instruks.bbr.dk/samletbygningsareal/0/31)
- [BBR: help on registered areas](https://bbr.dk/hjaelp-til-bbr)
- [BBR: area concepts at building level](https://instruks.bbr.dk/arealebygningsniveau/0/30)

## Total-floor-area coverage by building use

{_markdown_table(("Building-use group", "Buildings", "Missing total floor area"), use_rows)}

This breakdown matters because missing total floor area is structural rather
than random. In particular, small detached structures are represented by
footprint while BBR does not permit total floor area for use codes 910-930.
{non_outbuilding_summary} This is much more informative than the overall 54.84%
missing rate, which is dominated by small structures.

## Output tables

- `results/data_quality_dataset_summary.csv`: dataset size, temporal coverage
  and versions per ID.
- `results/data_quality_critical_missingness.csv`: missing and zero values for
  fields needed by the planned analysis.
- `results/data_quality_area_fields.csv`: coverage and distributions for all
  true area-measurement columns in `Bygning`.
- `results/data_quality_area_by_use.csv`: principal-area coverage by building
  use group.
- `results/data_quality_area_consistency.csv`: supporting availability
  patterns, component checks, and floor-area-to-footprint diagnostics.

The two columns whose names contain `Areal` but are actually codes,
`byg052BeregningsprincipCarportAreal` and `byg053BygningsarealerKilde`, are
intentionally excluded from the area-measurement table.
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")


def run_assessment(
    input_dir: Path,
    output_dir: Path,
    report_path: Path,
    *,
    make_plot: bool = True,
) -> dict[str, pl.DataFrame]:
    """Run all quality checks and write the report artifacts."""
    scans = {
        entity: pl.scan_parquet(input_dir / f"{entity}.parquet")
        for entity in ("bygning", "bbrsag", "sagsniveau")
    }
    summaries = [summarize_dataset(entity, lf) for entity, lf in scans.items()]
    dataset_summary = pl.concat(summaries, how="vertical")

    missingness_frames = []
    for entity, lf in scans.items():
        missingness_frames.append(
            summarize_missingness(entity, "temporal_rows", lf, CRITICAL_COLUMNS[entity])
        )
        missingness_frames.append(
            summarize_missingness(
                entity,
                "currently_effective",
                currently_effective(lf),
                CRITICAL_COLUMNS[entity],
            )
        )

    building_current = currently_effective(scans["bygning"])
    status_10 = building_current.filter(pl.col("status") == 10)
    not_status_10 = building_current.filter(pl.col("status") != 10)
    for scope, frame in (
        ("currently_effective_status_10", status_10),
        ("currently_effective_not_status_10", not_status_10),
    ):
        missingness_frames.append(
            summarize_missingness("bygning", scope, frame, CRITICAL_COLUMNS["bygning"])
        )

    critical_missingness = pl.concat(missingness_frames, how="vertical")
    area_stats = pl.concat(
        [
            summarize_area_fields("temporal_rows", scans["bygning"]),
            summarize_area_fields("currently_effective", building_current),
            summarize_area_fields("currently_effective_status_10", status_10),
            summarize_area_fields("currently_effective_not_status_10", not_status_10),
        ],
        how="vertical",
    )
    area_by_use = pl.concat(
        [
            summarize_area_by_use(building_current, "currently_effective"),
            summarize_area_by_use(status_10, "currently_effective_status_10"),
        ],
        how="vertical",
    )
    area_consistency = pl.concat(
        [
            summarize_area_consistency(building_current, "currently_effective"),
            summarize_area_consistency(status_10, "currently_effective_status_10"),
        ],
        how="vertical",
    )

    outputs = {
        "dataset_summary": dataset_summary,
        "critical_missingness": critical_missingness,
        "area_fields": area_stats,
        "area_by_use": area_by_use,
        "area_consistency": area_consistency,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in outputs.items():
        frame.write_csv(output_dir / f"data_quality_{name}.csv")

    if make_plot:
        _write_area_plot(
            area_stats, output_dir / "figures" / "data_quality_area_missingness.png"
        )
    render_report(
        dataset_summary,
        critical_missingness,
        area_stats,
        area_by_use,
        report_path,
    )
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assess coverage and area quality in the cleaned temporal BBR data."
    )
    parser.add_argument("--input-dir", type=Path, default=Path("dataset/clean"))
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("docs/data_quality_report.md"),
    )
    parser.add_argument("--no-plot", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(f"Assessing cleaned BBR data in {args.input_dir}", flush=True)
    outputs = run_assessment(
        args.input_dir,
        args.output_dir,
        args.report,
        make_plot=not args.no_plot,
    )
    summary = outputs["dataset_summary"]
    for row in summary.iter_rows(named=True):
        print(
            f"{row['entity']}: {row['temporal_rows']:,} rows, "
            f"{row['unique_ids']:,} unique IDs",
            flush=True,
        )
    print(f"Wrote report to {args.report}", flush=True)


if __name__ == "__main__":
    main()
