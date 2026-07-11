"""Non-destructive cleaning for temporal BBR CSV extracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import polars as pl

from .classifications import add_documented_classifications
from .entity_specs import ENTITY_SPECS, EntitySpec


@dataclass(frozen=True)
class CleaningResult:
    entity: str
    input_path: Path
    output_path: Path
    columns: tuple[str, ...]
    output_bytes: int


def _existing(columns: Iterable[str], available: set[str]) -> list[str]:
    return sorted(set(columns) & available)


def validate_columns(columns: Iterable[str], spec: EntitySpec) -> None:
    """Fail early when the extract does not match the expected entity schema."""
    available = set(columns)
    missing = sorted(spec.required_columns - available)
    if missing:
        raise ValueError(
            f"{spec.name} is missing required columns: {', '.join(missing)}"
        )


def scan_clean_temporal_csv(
    input_path: str | Path,
    spec: EntitySpec,
    *,
    n_rows: int | None = None,
    select_columns: Iterable[str] | None = None,
) -> pl.LazyFrame:
    """Return a typed LazyFrame while preserving every temporal observation.

    CSV columns are initially read as strings so a rare value late in a large file
    cannot invalidate an inferred schema. Only documented columns are then cast.
    Casts are strict so unexpected non-null values stop the conversion instead of
    being silently discarded.
    """
    source = Path(input_path)
    if not source.is_file():
        raise FileNotFoundError(source)

    lf = pl.scan_csv(
        source,
        infer_schema=False,
        n_rows=n_rows,
        null_values="",
        low_memory=True,
        rechunk=False,
    )
    source_columns = lf.collect_schema().names()
    validate_columns(source_columns, spec)

    if select_columns is not None:
        requested = list(dict.fromkeys(select_columns))
        missing = sorted(set(requested) - set(source_columns))
        if missing:
            raise ValueError(f"Unknown columns requested: {', '.join(missing)}")
        lf = lf.select(requested)
        source_columns = requested

    available = set(source_columns)
    expressions: list[pl.Expr] = []

    for column in _existing(spec.datetime_columns, available):
        expressions.append(
            pl.col(column).str.to_datetime(strict=True, time_zone="UTC").alias(column)
        )

    for column in _existing(spec.integer_columns, available):
        expressions.append(pl.col(column).cast(pl.Int64, strict=True).alias(column))

    for column in _existing(spec.code_columns, available):
        expressions.append(pl.col(column).cast(pl.Int32, strict=True).alias(column))

    for column in _existing(spec.id_columns, available):
        expressions.append(
            pl.col(column).str.strip_chars().str.to_lowercase().alias(column)
        )

    if "kommunekode" in available:
        expressions.append(
            pl.col("kommunekode")
            .str.strip_chars()
            .str.zfill(4)
            .alias("kommunekode")
        )

    return add_documented_classifications(lf.with_columns(expressions), spec.name)


def clean_entity_csv(
    input_path: str | Path,
    output_path: str | Path,
    entity: str,
    *,
    n_rows: int | None = None,
    select_columns: Iterable[str] | None = None,
    overwrite: bool = False,
    compression: str = "zstd",
) -> CleaningResult:
    """Stream a temporal BBR CSV into an atomically replaced Parquet file."""
    try:
        spec = ENTITY_SPECS[entity.lower()]
    except KeyError as exc:
        choices = ", ".join(sorted(ENTITY_SPECS))
        raise ValueError(f"Unknown entity {entity!r}; expected one of: {choices}") from exc

    source = Path(input_path)
    destination = Path(output_path)
    if destination.exists() and not overwrite:
        raise FileExistsError(
            f"Output already exists: {destination}. Pass overwrite=True to replace it."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.partial")
    temporary.unlink(missing_ok=True)

    lf = scan_clean_temporal_csv(
        source,
        spec,
        n_rows=n_rows,
        select_columns=select_columns,
    )
    columns = tuple(lf.collect_schema().names())

    try:
        lf.sink_parquet(
            temporary,
            compression=compression,
            statistics=True,
            maintain_order=True,
            engine="streaming",
        )
        temporary.replace(destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise

    return CleaningResult(
        entity=spec.name,
        input_path=source,
        output_path=destination,
        columns=columns,
        output_bytes=destination.stat().st_size,
    )


def clean_bygning_csv(
    input_path: str | Path, output_path: str | Path, **kwargs: Any
) -> CleaningResult:
    """Clean a temporal Bygning CSV without collapsing its history."""
    return clean_entity_csv(input_path, output_path, "bygning", **kwargs)


def clean_bbrsag_csv(
    input_path: str | Path, output_path: str | Path, **kwargs: Any
) -> CleaningResult:
    """Clean a temporal BBRSag CSV without collapsing its history."""
    return clean_entity_csv(input_path, output_path, "bbrsag", **kwargs)


def clean_sagsniveau_csv(
    input_path: str | Path, output_path: str | Path, **kwargs: Any
) -> CleaningResult:
    """Clean a temporal Sagsniveau CSV without collapsing its history."""
    return clean_entity_csv(input_path, output_path, "sagsniveau", **kwargs)
