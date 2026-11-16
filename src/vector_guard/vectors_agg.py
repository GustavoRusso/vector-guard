"""Aggregate interim vectors into species-monthly training tables.

Contract: ``data/03_processed/vectors_species_monthly.parquet``
(see ``specs/04-reference-data-and-panel-pipeline.md``).
"""

from __future__ import annotations

import pandas as pd

SPECIES_MONTHLY_KEYS: list[str] = [
    "h3_cell",
    "year",
    "month",
    "scientific_name",
    "vector_group",
]

SPECIES_MONTHLY_COLS: list[str] = SPECIES_MONTHLY_KEYS + [
    "individual_count",
    "observation_count",
    "sampling_protocol_count",
]


def _key_present(series: pd.Series) -> pd.Series:
    """True when a group key is non-null and (for strings) non-empty after strip."""
    if pd.api.types.is_numeric_dtype(series):
        return series.notna()
    as_str = series.astype("string")
    return as_str.notna() & (as_str.str.strip() != "")


def aggregate_vectors_species_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate interim vectors to H3 × month × species effort rows.

    Drops rows missing any of ``SPECIES_MONTHLY_KEYS``. Sums numeric-coerced
    ``individual_count``, counts rows as ``observation_count``, and counts
    distinct non-null ``sampling_protocol`` values.
    """
    missing = [c for c in SPECIES_MONTHLY_KEYS + ["individual_count", "sampling_protocol"] if c not in df.columns]
    if missing:
        raise ValueError(f"interim vectors missing columns: {missing}")

    work = df.copy()
    key_ok = pd.Series(True, index=work.index)
    for col in SPECIES_MONTHLY_KEYS:
        key_ok &= _key_present(work[col])
    work = work.loc[key_ok].copy()

    work["_ic"] = pd.to_numeric(work["individual_count"], errors="coerce")

    out = (
        work.groupby(SPECIES_MONTHLY_KEYS, dropna=False)
        .agg(
            individual_count=("_ic", "sum"),
            observation_count=("scientific_name", "size"),
            sampling_protocol_count=("sampling_protocol", "nunique"),
        )
        .reset_index()
    )

    out["individual_count"] = out["individual_count"].fillna(0.0)
    out["observation_count"] = out["observation_count"].astype("int64")
    out["sampling_protocol_count"] = out["sampling_protocol_count"].astype("int64")
    return out.loc[:, SPECIES_MONTHLY_COLS].reset_index(drop=True)
