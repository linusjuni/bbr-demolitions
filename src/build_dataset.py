"""Build the slim analysis dataset.

Reads the raw BBR extract (cleaned_dataset.csv + fullBBR.csv), keeps only the
columns and rows needed for the ablation, attaches the re-registration
cross-check flag, and writes dataset/demolitions.parquet.

Heavy step — run once, requires the raw source data.

TODO: implement.
"""
