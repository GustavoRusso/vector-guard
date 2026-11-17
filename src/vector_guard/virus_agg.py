"""Aggregate interim viruses into monthly detection tables.

Contract: ``data/03_processed/virus_monthly.parquet``
(see ``specs/04-reference-data-and-panel-pipeline.md``).
"""

from __future__ import annotations

import pandas as pd

VIRUS_MONTHLY_KEYS: list[str] = [
    "h3_cell",
    "country_iso2",
    "year",
    "month",
    "pathogen_name",
    "host_group",
    "host",
]

VIRUS_MONTHLY_COLS: list[str] = VIRUS_MONTHLY_KEYS + [
    "detections_count",
]

# Inclusion filter only (groupby still uses all VIRUS_MONTHLY_KEYS).
_VIRUS_MONTHLY_REQUIRED: list[str] = ["h3_cell", "year", "month"]


def _key_present(series: pd.Series) -> pd.Series:
    """True when a group key is non-null and (for strings) non-empty after strip."""
    if pd.api.types.is_numeric_dtype(series):
        return series.notna()
    as_str = series.astype("string")
    return as_str.notna() & (as_str.str.strip() != "")


def aggregate_virus_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate interim viruses to H3 × month × pathogen × host rows.

    Keeps rows with non-empty ``h3_cell`` and non-null ``year`` / ``month``.
    Other group keys may be empty. Counts rows as ``detections_count``.
    """
    missing = [c for c in VIRUS_MONTHLY_KEYS if c not in df.columns]
    if missing:
        raise ValueError(f"interim viruses missing columns: {missing}")

    work = df.copy()
    key_ok = pd.Series(True, index=work.index)
    for col in _VIRUS_MONTHLY_REQUIRED:
        key_ok &= _key_present(work[col])
    work = work.loc[key_ok].copy()

    out = (
        work.groupby(VIRUS_MONTHLY_KEYS, dropna=False)
        .size()
        .reset_index(name="detections_count")
    )
    out["detections_count"] = out["detections_count"].astype("int64")
    return out.loc[:, VIRUS_MONTHLY_COLS].reset_index(drop=True)
