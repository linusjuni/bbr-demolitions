# BBR Demolitions

Reproducibility repository for our article.

## Findings (one paragraph)

The headline BBR demolition statistics are not robust to indicator choice. Naive definition might lead to wrong conclusions.

## Data availability

TODO: We will make: `dataset/demolitions.parquet`

## Cleaning temporal BBR extracts

The canonical cleaning layer preserves every temporal observation and every
source column from `Bygning`, `BBRSag`, and `Sagsniveau`. It normalizes known
types and writes compressed Parquet without applying a demolition definition.
It also appends `region_name`, using Statistics Denmark's municipality-region
classification valid from 2007, and `building_use_group` to `Bygning`, using a
fine aggregation of the official BBR use-code hierarchy. The original codes
remain available for alternative classifications.

Run a bounded validation conversion first:

```bash
.venv/bin/python -m src.cleaning.clean_temporal_bbr \
  --n-rows 10000 \
  --output-dir /tmp/bbr-clean-sample
```

After reviewing the sample outputs and available disk space, run the complete
conversion:

```bash
.venv/bin/python -m src.cleaning.clean_temporal_bbr
```

Outputs are written to `dataset/clean/` and are intentionally not committed.
Use `--entity bygning`, `--entity bbrsag`, or `--entity sagsniveau` to process a
single extract. Existing outputs are protected unless `--overwrite` is passed.
The detailed description is in [docs/cleaning.md](docs/cleaning.md).

## Data-quality assessment

Generate coverage, missingness, and building-area diagnostics with:

```bash
.venv/bin/python -m src.data_quality
```

This writes small result tables to `results/`, an area-coverage figure, and the
readable report at [docs/data_quality_report.md](docs/data_quality_report.md).
The shared rules for indicator filtering and area reporting are documented in
[docs/analysis_filters.md](docs/analysis_filters.md).

## Authors

Linus, Theodor, Oscar (DTU/EPFL).
