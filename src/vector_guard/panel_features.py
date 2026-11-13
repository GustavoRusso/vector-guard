"""Panel feature helpers for EDA / modelling prep."""

from __future__ import annotations

import pandas as pd

# Observed VectorNet unit (before pathogen explosion). No pathogen_name.
UNIT_KEY_COLS: list[str] = [
    "spatial_tier",
    "h3_cell",
    "country_iso2",
    "year",
    "month",
    "vector_group",
]

_SPECIES_LONG_REQUIRED = UNIT_KEY_COLS + ["scientific_name", "detection_count"]


def _merge_key_frame(df: pd.DataFrame, keys: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Copy join keys with NA sentinels so pandas merge matches nulls (Tier 2)."""
    out = df.copy()
    merge_keys: list[str] = []
    for col in keys:
        mk = f"_mk_{col}"
        merge_keys.append(mk)
        if pd.api.types.is_numeric_dtype(out[col]):
            out[mk] = out[col].fillna(-1)
        else:
            out[mk] = out[col].astype("string").fillna("__NA__")
    return out, merge_keys


def priority_count_columns(priority_taxa: pd.DataFrame) -> list[str]:
    """Closed modelling columns ``vector_count_<feature_slug>``."""
    slugs = priority_taxa["feature_slug"].astype(str).tolist()
    return [f"vector_count_{slug}" for slug in slugs]


def pivot_priority_species_at_units(
    species_long: pd.DataFrame,
    priority_taxa: pd.DataFrame,
    *,
    unit_keys: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Pivot long species counts to wide priority columns at **unit** grain.

    Grain of ``species_long``: one row per unit × ``scientific_name`` (no
    ``pathogen_name``). Only taxa in ``priority_taxa`` become columns; absent
    taxa are ``0``. If ``unit_keys`` is given, restrict and left-align to those
    units so every filtered panel unit gets a wide row.
    """
    missing = [c for c in _SPECIES_LONG_REQUIRED if c not in species_long.columns]
    if missing:
        raise ValueError(f"species_long missing columns: {missing}")

    name_to_slug = (
        priority_taxa.drop_duplicates(subset=["scientific_name"])
        .set_index("scientific_name")["feature_slug"]
        .astype(str)
        .to_dict()
    )
    slugs = priority_taxa["feature_slug"].astype(str).tolist()
    count_cols = [f"vector_count_{slug}" for slug in slugs]

    work = species_long.loc[:, _SPECIES_LONG_REQUIRED].copy()
    if unit_keys is not None:
        units = unit_keys.loc[:, UNIT_KEY_COLS].drop_duplicates()
        left, mkeys = _merge_key_frame(units, UNIT_KEY_COLS)
        right, _ = _merge_key_frame(work, UNIT_KEY_COLS)
        # Keep unit keys from the left only (avoid _x/_y suffixes).
        right = right.drop(columns=UNIT_KEY_COLS)
        work = left.merge(right, on=mkeys, how="inner").drop(columns=mkeys)

    work["_slug"] = work["scientific_name"].map(name_to_slug)
    work = work.loc[work["_slug"].notna()].copy()

    if unit_keys is not None:
        base = unit_keys.loc[:, UNIT_KEY_COLS].drop_duplicates().copy()
    else:
        base = work.loc[:, UNIT_KEY_COLS].drop_duplicates().copy()

    if work.empty:
        wide = base.copy()
        for col in count_cols:
            wide[col] = 0
        return wide.reset_index(drop=True)

    tall = (
        work.groupby(UNIT_KEY_COLS + ["_slug"], dropna=False)["detection_count"]
        .sum()
        .reset_index()
    )
    pivoted = (
        tall.pivot_table(
            index=UNIT_KEY_COLS,
            columns="_slug",
            values="detection_count",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )
    pivoted.columns = [
        c if c in UNIT_KEY_COLS else f"vector_count_{c}" for c in pivoted.columns
    ]

    base_m, mkeys = _merge_key_frame(base, UNIT_KEY_COLS)
    piv_m, _ = _merge_key_frame(pivoted, UNIT_KEY_COLS)
    piv_m = piv_m.drop(columns=UNIT_KEY_COLS)
    wide = base_m.merge(piv_m, on=mkeys, how="left").drop(columns=mkeys)
    for col in count_cols:
        if col not in wide.columns:
            wide[col] = 0
        wide[col] = wide[col].fillna(0).astype(int)
    return wide.loc[:, UNIT_KEY_COLS + count_cols].reset_index(drop=True)


def attach_priority_species_features(
    panel: pd.DataFrame,
    species_long: pd.DataFrame,
    priority_taxa: pd.DataFrame,
) -> pd.DataFrame:
    """Attach priority ``vector_count_*`` via unit-grain pivot, then merge.

    Correct order (pathogen-long panel):

    1. Distinct unit keys from ``panel``
    2. Restrict + pivot ``species_long`` at unit grain
    3. Left-merge wide counts onto ``panel`` (broadcast across pathogens)

    Do **not** join species-long onto pathogen-long rows before pivoting.
    """
    n_in = len(panel)
    out = panel.copy()
    drop_cols = [c for c in out.columns if c.startswith("vector_count_")]
    if drop_cols:
        out = out.drop(columns=drop_cols)

    unit_keys = out.loc[:, UNIT_KEY_COLS].drop_duplicates()
    wide = pivot_priority_species_at_units(
        species_long, priority_taxa, unit_keys=unit_keys
    )
    count_cols = priority_count_columns(priority_taxa)

    left, mkeys = _merge_key_frame(out, UNIT_KEY_COLS)
    right, _ = _merge_key_frame(wide, UNIT_KEY_COLS)
    right = right.drop(columns=UNIT_KEY_COLS)
    merged = left.merge(right, on=mkeys, how="left").drop(columns=mkeys)
    for col in count_cols:
        merged[col] = merged[col].fillna(0).astype(int)

    if len(merged) != n_in:
        raise AssertionError(
            f"unit-grain species merge changed row count: {n_in} -> {len(merged)} "
            "(likely joined species-long before pivot)"
        )
    return merged.reset_index(drop=True)


def species_long_from_priority_wide(
    panel: pd.DataFrame,
    priority_taxa: pd.DataFrame,
) -> pd.DataFrame:
    """Transitional long table from existing wide ``vector_count_*`` on the panel.

    Dedupes to unit grain, melts non-zero priority counts. Used until
    ``modelling_panel_species.parquet`` is produced by merge notebook 10.
    """
    count_cols = priority_count_columns(priority_taxa)
    missing = [c for c in count_cols if c not in panel.columns]
    if missing:
        raise ValueError(f"panel missing priority columns: {missing[:5]}...")

    slug_to_name = (
        priority_taxa.drop_duplicates(subset=["feature_slug"])
        .set_index("feature_slug")["scientific_name"]
        .to_dict()
    )
    units = panel.loc[:, UNIT_KEY_COLS + count_cols].drop_duplicates(UNIT_KEY_COLS)
    long = units.melt(
        id_vars=UNIT_KEY_COLS,
        value_vars=count_cols,
        var_name="_count_col",
        value_name="detection_count",
    )
    long = long.loc[long["detection_count"].fillna(0).gt(0)].copy()
    long["feature_slug"] = long["_count_col"].str.removeprefix("vector_count_")
    long["scientific_name"] = long["feature_slug"].map(slug_to_name)
    long = long.loc[long["scientific_name"].notna()]
    long["detection_count"] = long["detection_count"].astype(int)
    return long.loc[:, _SPECIES_LONG_REQUIRED].reset_index(drop=True)
