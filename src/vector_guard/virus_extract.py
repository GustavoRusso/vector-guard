"""Normalize and deduplicate multi-source virus detection extracts.

Helpers for ``notebooks/03_extract_viruses.ipynb`` that implement the unified
raw schema and merge rules from ``specs/02-virus-dataset-selection.md``.
"""

from __future__ import annotations

import re
from typing import Iterable

import pandas as pd

from vector_guard.data import VIRUS_VECTOR_TAXON_MAP, VirusTaxonTarget

VIRUS_RAW_COLUMNS: tuple[str, ...] = (
    "record_id",
    "source",
    "accession",
    "sample_accession",
    "study_accession",
    "pathogen_name",
    "vector_group",
    "query_tax_id",
    "scientific_name",
    "tax_id",
    "country",
    "subnational_region",
    "nuts_id",
    "lat",
    "lon",
    "coord_source",
    "collection_date",
    "host",
    "isolation_source",
)

INSDC_SOURCES: tuple[str, ...] = (
    "ena_sequence",
    "ena_read_run",
    "bvbrc",
    "pathoplexus",
)

OUTBREAK_SOURCES: tuple[str, ...] = (
    "empres_i",
    "ecdc_atlas",
)

SOURCE_PRIORITY: dict[str, int] = {
    "ena_sequence": 0,
    "ena_read_run": 1,
    "bvbrc": 2,
    "pathoplexus": 3,
    "empres_i": 4,
    "ecdc_atlas": 5,
}

COORD_SOURCE_RANK: dict[str, int] = {
    "exact_gps": 0,
    "sample_backfill": 1,
    "none": 2,
    "": 2,
}

_ACCESSION_VERSION_RE = re.compile(r"\.\d+$")
_COORD_PAIR_RE = re.compile(
    r"(?P<lat>-?\d+(?:\.\d+)?)\s*(?P<lat_hem>[NnSs])?"
    r"(?:\s+|,)\s*"
    r"(?P<lon>-?\d+(?:\.\d+)?)\s*(?P<lon_hem>[EeWw])?",
    re.IGNORECASE,
)
_ISO_DATE_RE = re.compile(
    r"(?P<year>(?:19|20)\d{2})(?:-(?P<month>\d{2})(?:-(?P<day>\d{2}))?)?"
)
_ISO_WEEK_RE = re.compile(r"(?P<year>(?:19|20)\d{2})-W(?P<week>\d{1,2})", re.IGNORECASE)


def lineage_tax_ids(target: VirusTaxonTarget) -> tuple[int, ...]:
    """Return ICTV ``tax_ids`` plus ``legacy_tax_ids`` (deduplicated, order kept)."""
    seen: set[int] = set()
    out: list[int] = []
    for tax_id in (*target["tax_ids"], *target.get("legacy_tax_ids", ())):
        if tax_id in seen:
            continue
        seen.add(tax_id)
        out.append(tax_id)
    return tuple(out)


def empty_virus_frame(rows: Iterable[dict[str, object]] | None = None) -> pd.DataFrame:
    """Return an empty (or row-seeded) DataFrame with the canonical virus columns."""
    if rows is None:
        return pd.DataFrame(columns=list(VIRUS_RAW_COLUMNS))
    return ensure_virus_columns(pd.DataFrame(list(rows)))


def ensure_virus_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Reindex *df* onto ``VIRUS_RAW_COLUMNS``, coercing missing cells to ``""``."""
    out = df.copy()
    for column in VIRUS_RAW_COLUMNS:
        if column not in out.columns:
            out[column] = ""
    out = out.reindex(columns=list(VIRUS_RAW_COLUMNS))
    return out.fillna("").astype(str)


def normalize_accession(value: object) -> str:
    """Uppercase an INSDC accession and strip a trailing ``.version`` suffix."""
    text = str(value or "").strip()
    if not text or text.lower() in {"nan", "none", "null", "na", "n/a"}:
        return ""
    text = text.upper()
    return _ACCESSION_VERSION_RE.sub("", text)


def split_accessions(value: object) -> list[str]:
    """Split multi-accession strings (comma/semicolon/whitespace) and normalize."""
    text = str(value or "").strip()
    if not text:
        return []
    parts = re.split(r"[,;\s]+", text)
    out: list[str] = []
    seen: set[str] = set()
    for part in parts:
        accession = normalize_accession(part)
        if not accession or accession in seen:
            continue
        seen.add(accession)
        out.append(accession)
    return out


def pick_primary_accession(
    value: object,
    known_accessions: set[str] | None = None,
) -> str:
    """Prefer an accession already present in *known_accessions*, else the first.

    Segmented BV-BRC genomes publish several GenBank accessions; matching an
    existing ENA accession first avoids inventing extra detection rows.
    """
    accessions = split_accessions(value)
    if not accessions:
        return ""
    if known_accessions:
        for accession in accessions:
            if accession in known_accessions:
                return accession
    return accessions[0]


def _clean_text(value: object) -> str:
    text = str(value or "").strip()
    if text.lower() in {"nan", "none", "null", "na", "n/a", "no_value"}:
        return ""
    return text


def split_country_subnational(value: object) -> tuple[str, str]:
    """Return ``(country_field, subnational_region)`` from ENA-style place text.

    The full ENA-style token (``Country: region, locality``) is preserved in
    ``country`` for downstream alias matching; ``subnational_region`` holds the
    text after the first ``:`` when present.
    """
    text = _clean_text(value)
    if not text:
        return "", ""
    if ":" not in text:
        return text, ""
    _, region = text.split(":", 1)
    return text, region.strip(" ,;")


def parse_country_token(value: object) -> str:
    """Return the country token before ``:`` (or the whole string)."""
    text = _clean_text(value)
    if not text:
        return ""
    return text.split(":", 1)[0].strip()


def parse_subnational_token(value: object) -> str:
    """Return the subnational token after ``:`` when present."""
    _, region = split_country_subnational(value)
    return region


def _apply_hemisphere(magnitude: float, hemisphere: str | None, negative: str) -> float:
    if hemisphere and hemisphere.upper() in negative:
        return -abs(magnitude)
    if hemisphere and hemisphere.upper() not in negative and hemisphere.isalpha():
        return abs(magnitude)
    return magnitude


def format_coord(lat: float, lon: float) -> tuple[str, str]:
    """Validate WGS84 bounds and return decimal strings (or empty on failure)."""
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return "", ""
    if lat == 0.0 and lon == 0.0:
        # Treat exact Null Island as missing for surveillance metadata.
        return "", ""
    return (
        f"{lat:.8f}".rstrip("0").rstrip("."),
        f"{lon:.8f}".rstrip("0").rstrip("."),
    )


def parse_ena_location(value: object) -> tuple[str, str]:
    """Parse an ENA ``location`` string such as ``45.12 N 11.88 E`` into decimals."""
    text = _clean_text(value)
    if not text:
        return "", ""
    match = _COORD_PAIR_RE.search(text)
    if not match:
        return "", ""
    try:
        lat = float(match.group("lat"))
        lon = float(match.group("lon"))
    except ValueError:
        return "", ""
    lat = _apply_hemisphere(lat, match.group("lat_hem"), "S")
    lon = _apply_hemisphere(lon, match.group("lon_hem"), "W")
    return format_coord(lat, lon)


def parse_decimal_coord(lat: object, lon: object) -> tuple[str, str]:
    """Parse already-split decimal latitude / longitude fields."""
    lat_text = _clean_text(lat).replace(",", "")
    lon_text = _clean_text(lon).replace(",", "")
    if not lat_text or not lon_text:
        return "", ""
    try:
        return format_coord(float(lat_text), float(lon_text))
    except ValueError:
        return "", ""


def resolve_coords(
    *,
    lat: object = "",
    lon: object = "",
    location: object = "",
    coord_source: str = "exact_gps",
) -> tuple[str, str, str]:
    """Resolve ``(lat, lon, coord_source)`` from decimal fields or ENA location text.

    Parameters
    ----------
    coord_source:
        Source label to attach when coordinates resolve
        (``exact_gps`` or ``sample_backfill``).
    """
    parsed_lat, parsed_lon = parse_decimal_coord(lat, lon)
    if parsed_lat and parsed_lon:
        label = coord_source if coord_source in COORD_SOURCE_RANK else "exact_gps"
        return parsed_lat, parsed_lon, label

    parsed_lat, parsed_lon = parse_ena_location(location)
    if parsed_lat and parsed_lon:
        label = coord_source if coord_source in COORD_SOURCE_RANK else "exact_gps"
        return parsed_lat, parsed_lon, label

    return "", "", "none"


def has_place_or_time(df: pd.DataFrame) -> pd.Series:
    """Keep rows with usable place and/or time after source-specific parsing."""
    country = df.get("country", pd.Series("", index=df.index)).fillna("").map(_clean_text)
    nuts_id = df.get("nuts_id", pd.Series("", index=df.index)).fillna("").map(_clean_text)
    lat = df.get("lat", pd.Series("", index=df.index)).fillna("").map(_clean_text)
    lon = df.get("lon", pd.Series("", index=df.index)).fillna("").map(_clean_text)
    collected = (
        df.get("collection_date", pd.Series("", index=df.index)).fillna("").map(_clean_text)
    )
    has_coords = (lat != "") & (lon != "")
    return (country != "") | (nuts_id != "") | has_coords | (collected != "")


def apply_keep_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Filter *df* to rows with usable place and/or time."""
    if df.empty:
        return ensure_virus_columns(df)
    return ensure_virus_columns(df.loc[has_place_or_time(df)].copy())


def _prefer_text(current: str, candidate: str) -> str:
    return current if current else candidate


def _coord_rank(value: str) -> int:
    return COORD_SOURCE_RANK.get(value, 2)


def _source_rank(value: str) -> int:
    return SOURCE_PRIORITY.get(value, 99)


def _merge_insdc_rows(group: pd.DataFrame) -> dict[str, str]:
    """Merge one INSDC accession/sample group to the richest non-null metadata."""
    rows = ensure_virus_columns(group).to_dict(orient="records")
    rows.sort(key=lambda row: (_source_rank(row["source"]), row["record_id"], row["accession"]))

    primary = min(rows, key=lambda row: (_source_rank(row["source"]), row["record_id"]))
    merged = {column: "" for column in VIRUS_RAW_COLUMNS}
    merged["source"] = primary["source"]
    merged["pathogen_name"] = primary["pathogen_name"]
    merged["vector_group"] = primary["vector_group"]

    best_coord_rank = 99
    for row in rows:
        for column in (
            "accession",
            "sample_accession",
            "study_accession",
            "query_tax_id",
            "scientific_name",
            "tax_id",
            "country",
            "subnational_region",
            "nuts_id",
            "collection_date",
            "host",
            "isolation_source",
        ):
            merged[column] = _prefer_text(merged[column], row[column])

        row_rank = _coord_rank(row["coord_source"])
        row_has_coords = bool(row["lat"] and row["lon"])
        if row_has_coords and (
            not merged["lat"] or not merged["lon"] or row_rank < best_coord_rank
        ):
            merged["lat"] = row["lat"]
            merged["lon"] = row["lon"]
            merged["coord_source"] = row["coord_source"] or "exact_gps"
            best_coord_rank = row_rank

    if not merged["lat"] or not merged["lon"]:
        merged["lat"] = ""
        merged["lon"] = ""
        merged["coord_source"] = "none"
    elif not merged["coord_source"]:
        merged["coord_source"] = "exact_gps"

    native = merged["accession"] or merged["sample_accession"] or primary.get("record_id", "")
    native = native.replace(f"{merged['source']}:", "", 1)
    merged["record_id"] = f"{merged['source']}:{native}" if native else merged["source"]
    return merged


def dedupe_insdc(df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate INSDC-backed rows by accession, else sample_accession + pathogen."""
    frame = ensure_virus_columns(df)
    if frame.empty:
        return frame

    insdc = frame.loc[frame["source"].isin(INSDC_SOURCES)].copy()
    if insdc.empty:
        return empty_virus_frame()

    insdc["accession"] = insdc["accession"].map(normalize_accession)
    insdc["sample_accession"] = insdc["sample_accession"].map(_clean_text)
    insdc["_group_key"] = ""

    has_accession = insdc["accession"] != ""
    insdc.loc[has_accession, "_group_key"] = "acc:" + insdc.loc[has_accession, "accession"]

    needs_sample = ~has_accession & (insdc["sample_accession"] != "")
    # Multi-virus BioSamples must not collapse distinct pathogens.
    sample_counts = (
        insdc.loc[insdc["sample_accession"] != ""]
        .groupby("sample_accession")["pathogen_name"]
        .nunique()
    )
    multi_sample = set(sample_counts.loc[sample_counts > 1].index)
    for idx in insdc.index[needs_sample]:
        sample = insdc.at[idx, "sample_accession"]
        pathogen = insdc.at[idx, "pathogen_name"]
        if sample in multi_sample:
            insdc.at[idx, "_group_key"] = f"sample:{sample}|{pathogen}"
        else:
            insdc.at[idx, "_group_key"] = f"sample:{sample}"

    singleton = insdc["_group_key"] == ""
    insdc.loc[singleton, "_group_key"] = [
        f"row:{source}:{idx}"
        for source, idx in zip(
            insdc.loc[singleton, "source"],
            insdc.loc[singleton].index.astype(str),
            strict=True,
        )
    ]

    merged_rows = [
        _merge_insdc_rows(group) for _, group in insdc.groupby("_group_key", sort=False)
    ]
    return ensure_virus_columns(pd.DataFrame(merged_rows))


def _round_coord(value: str, digits: int = 4) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    try:
        return f"{float(text):.{digits}f}"
    except ValueError:
        return text


def parse_collection_sort_key(value: object) -> tuple[int, int, int, int]:
    """Return a sortable ``(precision, year, month, day)`` key for outbreak dates.

    Lower precision ranks are preferred (day < month < year < ISO-week < unknown)
    so the earliest *specific* onset wins when deduplicating ECDC rows.
    """
    text = _clean_text(value)
    if not text:
        return (9, 9999, 99, 99)

    week = _ISO_WEEK_RE.search(text)
    if week:
        return (3, int(week.group("year")), int(week.group("week")), 0)

    match = _ISO_DATE_RE.search(text)
    if not match:
        year_only = re.search(r"(?:19|20)\d{2}", text)
        if not year_only:
            return (9, 9999, 99, 99)
        return (4, int(year_only.group(0)), 99, 99)

    year = int(match.group("year"))
    month = int(match.group("month") or 99)
    day = int(match.group("day") or 99)
    if match.group("day"):
        precision = 0
    elif match.group("month"):
        precision = 1
    else:
        precision = 2
    return (precision, year, month, day)


def _outbreak_group_key(row: pd.Series) -> str:
    source = row["source"]
    native = _clean_text(row["record_id"]).replace(f"{source}:", "", 1)
    if source == "empres_i" and native:
        return f"empres:{native}"
    if source == "empres_i":
        return "|".join(
            [
                "empres",
                row["pathogen_name"],
                _round_coord(row["lat"]),
                _round_coord(row["lon"]),
                _clean_text(row["collection_date"]),
            ]
        )
    if source == "ecdc_atlas":
        sort_key = parse_collection_sort_key(row["collection_date"])
        season_year = sort_key[1]
        nuts = _clean_text(row["nuts_id"]) or _clean_text(row["subnational_region"])
        return f"ecdc|{row['pathogen_name']}|{nuts}|{season_year}"
    return f"{source}:{native or row.name}"


def _prefer_outbreak_row(left: pd.Series, right: pd.Series) -> pd.Series:
    left_key = parse_collection_sort_key(left["collection_date"])
    right_key = parse_collection_sort_key(right["collection_date"])
    if right_key < left_key:
        return right
    if left_key < right_key:
        return left
    # Same date specificity: prefer richer geo / host metadata.
    left_score = sum(
        bool(_clean_text(left[column]))
        for column in ("lat", "lon", "nuts_id", "subnational_region", "host", "country")
    )
    right_score = sum(
        bool(_clean_text(right[column]))
        for column in ("lat", "lon", "nuts_id", "subnational_region", "host", "country")
    )
    return right if right_score > left_score else left


def dedupe_outbreak(df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate outbreak / surveillance rows without collapsing into INSDC."""
    frame = ensure_virus_columns(df)
    if frame.empty:
        return frame

    outbreak = frame.loc[frame["source"].isin(OUTBREAK_SOURCES)].copy()
    if outbreak.empty:
        return empty_virus_frame()

    outbreak["_group_key"] = outbreak.apply(_outbreak_group_key, axis=1)
    kept: list[dict[str, str]] = []
    for _, group in outbreak.groupby("_group_key", sort=False):
        chosen = group.iloc[0]
        for _, row in group.iloc[1:].iterrows():
            chosen = _prefer_outbreak_row(chosen, row)
        kept.append(ensure_virus_columns(pd.DataFrame([chosen])).iloc[0].to_dict())
    return ensure_virus_columns(pd.DataFrame(kept))


def assign_record_ids(df: pd.DataFrame, *, native_id_column: str | None = None) -> pd.DataFrame:
    """Fill blank ``record_id`` values as ``{source}:{native_id}``."""
    out = ensure_virus_columns(df)
    if out.empty:
        return out

    for idx, row in out.iterrows():
        if _clean_text(row["record_id"]):
            continue
        source = _clean_text(row["source"]) or "unknown"
        if native_id_column and _clean_text(row.get(native_id_column, "")):
            native = _clean_text(row[native_id_column])
        else:
            native = (
                _clean_text(row["accession"])
                or _clean_text(row["sample_accession"])
                or _clean_text(row["nuts_id"])
                or str(idx)
            )
        out.at[idx, "record_id"] = f"{source}:{native}"
    return out


def dedupe_virus_detections(df: pd.DataFrame) -> pd.DataFrame:
    """Apply INSDC and outbreak dedupe rules, then concatenate."""
    frame = assign_record_ids(ensure_virus_columns(df))
    if frame.empty:
        return frame

    insdc = dedupe_insdc(frame.loc[frame["source"].isin(INSDC_SOURCES)])
    outbreak = dedupe_outbreak(frame.loc[frame["source"].isin(OUTBREAK_SOURCES)])
    other = frame.loc[~frame["source"].isin((*INSDC_SOURCES, *OUTBREAK_SOURCES))]
    parts = [part for part in (insdc, outbreak, other) if not part.empty]
    if not parts:
        return empty_virus_frame()
    return ensure_virus_columns(pd.concat(parts, ignore_index=True))


def pathogen_lookup() -> dict[str, VirusTaxonTarget]:
    """Map canonical pathogen name → taxonomy target."""
    return {target["pathogen"]: target for target in VIRUS_VECTOR_TAXON_MAP}
