"""Command-line entry point for cleaning temporal BBR CSV extracts."""

from __future__ import annotations

import argparse
from pathlib import Path

from .entity_specs import ENTITY_SPECS
from .temporal_cleaner import clean_entity_csv


DEFAULT_INPUTS = {
    "bygning": "BBR_V3_Bygning_TotalDownload_csv_Temporal_688.csv",
    "bbrsag": "BBR_V3_BBRSag_TotalDownload_csv_Temporal_688.csv",
    "sagsniveau": "BBR_V3_Sagsniveau_TotalDownload_csv_Temporal_688.csv",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert temporal BBR CSV entities to typed, history-preserving Parquet files."
        )
    )
    parser.add_argument(
        "--entity",
        choices=["all", *sorted(ENTITY_SPECS)],
        default="all",
    )
    parser.add_argument("--input-dir", type=Path, default=Path("dataset/raw"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("dataset/clean")
    )
    parser.add_argument(
        "--n-rows",
        type=int,
        default=None,
        help="Clean only the first N rows; intended for validation runs.",
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    entities = sorted(ENTITY_SPECS) if args.entity == "all" else [args.entity]

    for entity in entities:
        source = args.input_dir / DEFAULT_INPUTS[entity]
        destination = args.output_dir / f"{entity}.parquet"
        print(f"Cleaning {entity}: {source} -> {destination}", flush=True)
        result = clean_entity_csv(
            source,
            destination,
            entity,
            n_rows=args.n_rows,
            overwrite=args.overwrite,
        )
        size_mib = result.output_bytes / (1024**2)
        print(
            f"Finished {entity}: {len(result.columns)} columns, {size_mib:.1f} MiB",
            flush=True,
        )


if __name__ == "__main__":
    main()
