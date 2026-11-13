"""Resolve country, coordinates, H3, and year-month for clean / merge notebooks.

Implements the locked ladder from ``specs/03`` / ``specs/04`` used by planned
notebooks ``07``–``10``. Does not invent free-text geocodes; unmatched regions
stay ``country_only``.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Mapping

import h3
import pandas as pd

from vector_guard.data import (
    default_interim_dir,
    default_reference_dir,
)
from vector_guard.virus_extract import (
    parse_collection_sort_key,
    parse_country_token,
    parse_decimal_coord,
)

# Locked in ``notebooks/01_sources/07_h3_resolution_density.ipynb`` (spec ``04``):
# finest candidate (4 vs 5) with usable Tier 1 co-occurrence under exact+centroid.
H3_RESOLUTION: int = 4

GEO_PRECISION_EXACT = "exact_coords"
GEO_PRECISION_CENTROID = "subnational_centroid"
GEO_PRECISION_COUNTRY = "country_only"
GEO_PRECISIONS: frozenset[str] = frozenset(
    {GEO_PRECISION_EXACT, GEO_PRECISION_CENTROID, GEO_PRECISION_COUNTRY}
)

# VectorNet publishes UK / EL; ISO 3166-1 uses GB / GR.
VECTORNET_CODE_TO_ISO2: dict[str, str] = {"UK": "GB", "EL": "GR"}
ISO2_TO_VECTORNET_CODE: dict[str, str] = {"GB": "UK", "GR": "EL"}

_ISO2_RE = re.compile(r"^[A-Za-z]{2}$")

_VECTORS_INTERIM_NAME = "vectors_normalized.parquet"
_VIRUSES_INTERIM_NAME = "viruses_normalized.parquet"


def norm_key(text: object) -> str:
    """Casefold, strip accents/punctuation → hyphenated match key."""
    if text is None:
        return ""
    raw = str(text).strip()
    if not raw:
        return ""
    s = unicodedata.normalize("NFKD", raw)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.casefold().strip().replace("&", " and ")
    s = re.sub(r"['`´]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


def _clean_text(value: object) -> str:
    text = str(value or "").strip()
    if text.lower() in {"nan", "none", "null", "na", "n/a", "no_value", "<na>"}:
        return ""
    return text


_ADMIN_SUFFIX_RE = re.compile(
    r"\b(province|region|state|county|oblast|department|prefecture|republic)\b",
    flags=re.IGNORECASE,
)


def strip_admin_suffix(text: object) -> str:
    """Drop common admin-unit suffixes (``province``, ``county``, …)."""
    raw = _clean_text(text)
    if not raw:
        return ""
    return _ADMIN_SUFFIX_RE.sub("", raw).strip(" ,/-")


def region_candidate_keys(region: object) -> list[str]:
    """Ordered normalized keys for a free-text ``subnational_region``.

    Order (trailing-first for multi-token strings):

    1. Full string (+ admin-suffix-stripped variant)
    2. Trailing segments after ``,`` / `` - `` / ``;`` (more specific admin)
    3. Leading segments
    4. Any remaining middle tokens

    Parenthetical clutter is stripped before normalization. Does not invent
    coordinates — callers must look keys up in the curated centroid index.
    """
    text = _clean_text(region)
    if not text:
        return []

    raw_parts: list[str] = [text]

    if "," in text:
        parts = [p.strip() for p in text.split(",") if p.strip()]
        if len(parts) >= 2:
            raw_parts.append(parts[-1])
            raw_parts.append(parts[0])
            raw_parts.extend(parts[1:-1])
        else:
            raw_parts.extend(parts)

    if " - " in text:
        left, right = text.split(" - ", 1)
        left, right = left.strip(), right.strip()
        if right:
            raw_parts.append(right)
        if left:
            raw_parts.append(left)

    if ";" in text:
        parts = [p.strip() for p in text.split(";") if p.strip()]
        if len(parts) >= 2:
            raw_parts.append(parts[-1])
            raw_parts.append(parts[0])
            raw_parts.extend(parts[1:-1])
        else:
            raw_parts.extend(parts)

    keys: list[str] = []
    for part in raw_parts:
        cleaned = re.sub(r"\([^)]*\)", "", part).strip()
        if not cleaned:
            continue
        for variant in (cleaned, strip_admin_suffix(cleaned)):
            key = norm_key(variant)
            if key and key not in keys:
                keys.append(key)
    return keys


def load_countries(reference_dir: Path | None = None) -> pd.DataFrame:
    """Load ``data/external/countries.csv``."""
    directory = Path(reference_dir) if reference_dir is not None else default_reference_dir()
    path = directory / "countries.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run notebooks/01_sources/05_reference_countries.ipynb first."
        )
    return pd.read_csv(path, dtype={"iso2": str, "name": str, "name_aliases": str})


def load_subnational_locations(reference_dir: Path | None = None) -> pd.DataFrame:
    """Load ``data/external/subnational_locations.csv``."""
    directory = Path(reference_dir) if reference_dir is not None else default_reference_dir()
    path = directory / "subnational_locations.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run notebooks/01_sources/05_reference_countries.ipynb first."
        )
    return pd.read_csv(
        path,
        dtype={"country_iso2": str, "region_key": str, "region_type": str, "canonical_name": str},
    )


def load_vector_taxon_groups(reference_dir: Path | None = None) -> pd.DataFrame:
    """Load ``data/external/vector_taxon_groups.csv``."""
    directory = Path(reference_dir) if reference_dir is not None else default_reference_dir()
    path = directory / "vector_taxon_groups.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run notebooks/01_sources/06_reference_vector_groups.ipynb first."
        )
    return pd.read_csv(
        path,
        dtype={"scientific_name": str, "vector_group": str, "notes": str},
    )


def load_interim_vectors(interim_dir: Path | None = None) -> pd.DataFrame:
    """Load ``data/02_interim/vectors_normalized.parquet``."""
    directory = Path(interim_dir) if interim_dir is not None else default_interim_dir()
    path = directory / _VECTORS_INTERIM_NAME
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run notebooks/01_sources/08_clean_vectors.ipynb first."
        )
    return pd.read_parquet(path)


def load_interim_viruses(interim_dir: Path | None = None) -> pd.DataFrame:
    """Load ``data/02_interim/viruses_normalized.parquet``."""
    directory = Path(interim_dir) if interim_dir is not None else default_interim_dir()
    path = directory / _VIRUSES_INTERIM_NAME
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run notebooks/01_sources/09_clean_viruses.ipynb first."
        )
    return pd.read_parquet(path)


def build_name_to_iso2(countries_df: pd.DataFrame) -> dict[str, str]:
    """Map normalized country ``name`` / ``name_aliases`` → ISO-2 from reference CSV."""
    mapping: dict[str, str] = {}
    for row in countries_df.itertuples(index=False):
        iso2 = _clean_text(getattr(row, "iso2", "")).upper()
        if not iso2:
            continue
        name = _clean_text(getattr(row, "name", ""))
        if name:
            mapping[norm_key(name)] = iso2
        aliases = _clean_text(getattr(row, "name_aliases", ""))
        if aliases:
            for alias in aliases.split("|"):
                alias = alias.strip()
                if alias:
                    mapping[norm_key(alias)] = iso2
        # Also accept the ISO-2 code itself as a lookup key.
        mapping[norm_key(iso2)] = iso2
    return mapping


def build_valid_iso2_set(countries_df: pd.DataFrame) -> set[str]:
    """Return the set of ISO-2 codes present in ``countries.csv``."""
    return {
        _clean_text(value).upper()
        for value in countries_df["iso2"].tolist()
        if _clean_text(value)
    }


def normalize_vectornet_iso2(code: object) -> str:
    """Uppercase a 2-letter code and map VectorNet UK/EL → GB/GR."""
    text = _clean_text(code).upper()
    if not text:
        return ""
    return VECTORNET_CODE_TO_ISO2.get(text, text)


def resolve_vector_country_iso2(
    *,
    country_code: object = "",
    higher_geography_id: object = "",
    valid_iso2: set[str] | None = None,
) -> str:
    """Resolve VectorNet country to ISO-2.

    Prefer published ``countryCode`` when present; else the first two characters
    of ``higherGeographyID``. Apply VectorNet UK/EL remaps and optionally
    validate against ``countries.csv``.
    """
    code = _clean_text(country_code).upper()
    if not code or not _ISO2_RE.fullmatch(code):
        hg = _clean_text(higher_geography_id).upper()
        code = hg[:2] if len(hg) >= 2 and hg[:2].isalpha() else ""
    if not code:
        return ""
    iso2 = normalize_vectornet_iso2(code)
    if valid_iso2 is not None and iso2 not in valid_iso2:
        return ""
    return iso2


def resolve_virus_country_iso2(
    country: object,
    name_to_iso2: Mapping[str, str],
) -> str:
    """Map a virus ``country`` field (ENA-style allowed) via alias table → ISO-2."""
    token = parse_country_token(country)
    if not token:
        return ""
    mapped = name_to_iso2.get(norm_key(token), "")
    if mapped:
        return mapped
    # Accept a bare ISO-2 / VectorNet code when it is already a known value.
    upper = normalize_vectornet_iso2(token)
    if _ISO2_RE.fullmatch(upper) and upper in set(name_to_iso2.values()):
        return upper
    return ""


def build_subnational_centroid_index(
    subnational_df: pd.DataFrame,
) -> dict[tuple[str, str], tuple[float, float]]:
    """Index ``(country_iso2, region_key)`` → ``(lat, lon)`` from reference CSV."""
    index: dict[tuple[str, str], tuple[float, float]] = {}
    for row in subnational_df.itertuples(index=False):
        iso2 = _clean_text(getattr(row, "country_iso2", "")).upper()
        key = _clean_text(getattr(row, "region_key", ""))
        if not iso2 or not key:
            continue
        try:
            lat = float(getattr(row, "lat"))
            lon = float(getattr(row, "lon"))
        except (TypeError, ValueError):
            continue
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            continue
        if lat == 0.0 and lon == 0.0:
            continue
        index[(iso2, key)] = (lat, lon)
    return index


def lookup_subnational_centroid(
    country_iso2: object,
    *,
    subnational_region: object = "",
    nuts_id: object = "",
    centroid_index: Mapping[tuple[str, str], tuple[float, float]] | None = None,
    subnational_df: pd.DataFrame | None = None,
) -> tuple[float, float] | None:
    """Match ``(country_iso2, region_key)`` for region text or ``nuts_id``.

    Prefer ``nuts_id`` when both are provided (more specific). Region free-text
    uses :func:`region_candidate_keys` (trailing-first admin tokens). Never
    invents coordinates for unmatched keys.
    """
    iso2 = _clean_text(country_iso2).upper()
    if not iso2:
        return None

    if centroid_index is None:
        if subnational_df is None:
            raise ValueError("Pass centroid_index or subnational_df")
        centroid_index = build_subnational_centroid_index(subnational_df)

    candidates: list[str] = []
    nuts = _clean_text(nuts_id)
    if nuts:
        candidates.append(norm_key(nuts))
    candidates.extend(region_candidate_keys(subnational_region))

    seen: set[str] = set()
    for key in candidates:
        if not key or key in seen:
            continue
        seen.add(key)
        hit = centroid_index.get((iso2, key))
        if hit is not None:
            return hit
    return None


def parse_lat_lon(lat: object, lon: object) -> tuple[float, float] | None:
    """Parse decimal lat/lon; return None when missing or out of bounds."""
    lat_s, lon_s = parse_decimal_coord(lat, lon)
    if not lat_s or not lon_s:
        return None
    return float(lat_s), float(lon_s)


def resolve_coords_ladder(
    *,
    lat: object = "",
    lon: object = "",
    coord_source: object = "",
    country_iso2: object = "",
    subnational_region: object = "",
    nuts_id: object = "",
    centroid_index: Mapping[tuple[str, str], tuple[float, float]] | None = None,
    subnational_df: pd.DataFrame | None = None,
    allow_centroid: bool = True,
) -> tuple[float | None, float | None, str]:
    """Resolve ``(lat, lon, geo_precision)`` via the locked priority ladder.

    1. Valid GPS when ``coord_source`` is exact/backfill (or coords present without
       an explicit ``none`` source) → ``exact_coords``
    2. Curated subnational / NUTS centroid → ``subnational_centroid``
    3. Else → ``country_only`` with null coords
    """
    source = _clean_text(coord_source).lower()
    parsed = parse_lat_lon(lat, lon)
    # Path A: usable decimals win unless the extract explicitly marked ``none``.
    # Empty ``coord_source`` covers VectorNet rows (no such column).
    if parsed is not None and source != "none":
        return parsed[0], parsed[1], GEO_PRECISION_EXACT

    if allow_centroid:
        centroid = lookup_subnational_centroid(
            country_iso2,
            subnational_region=subnational_region,
            nuts_id=nuts_id,
            centroid_index=centroid_index,
            subnational_df=subnational_df,
        )
        if centroid is not None:
            return centroid[0], centroid[1], GEO_PRECISION_CENTROID

    return None, None, GEO_PRECISION_COUNTRY


def assign_h3(
    lat: float | None,
    lon: float | None,
    resolution: int,
) -> str | None:
    """Return H3 cell id for ``(lat, lon)`` at *resolution*, or None if invalid."""
    if lat is None or lon is None:
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    if lat == 0.0 and lon == 0.0:
        return None
    if resolution < 0 or resolution > 15:
        raise ValueError(f"H3 resolution must be 0–15, got {resolution}")
    return h3.latlng_to_cell(lat, lon, resolution)


def parse_year_month_virus(collection_date: object) -> tuple[int, int] | None:
    """Parse virus ``collection_date`` to ``(year, month)`` when month is known.

    Accepts ISO ``YYYY-MM(-DD)``, ENA ``dd-Mon-yyyy`` / ``Mon-yyyy``, and ISO
    week ``YYYY-Www`` (Monday of that week). Year-only values return ``None``
    (panel grain requires month).
    """
    precision, year, month, _day = parse_collection_sort_key(collection_date)
    # precision 0 = day, 1 = month; 2+ lack a calendar month.
    if precision not in (0, 1):
        return None
    if year < 1900 or year > 2100:
        return None
    if month < 1 or month > 12:
        return None
    return year, month


def parse_year_month_vectornet(event_date: object) -> tuple[int, int] | None:
    """Parse VectorNet ``eventDate`` (point or ``start/end``) to midpoint year-month.

    One-sided intervals collapse to the available bound. Inverted intervals are
    ordered before taking the midpoint. Missing / unparseable → ``None``.
    """
    text = _clean_text(event_date)
    if not text:
        return None

    parts = text.split("/", 1)
    start = pd.to_datetime(parts[0].strip(), errors="coerce")
    end = (
        pd.to_datetime(parts[1].strip(), errors="coerce")
        if len(parts) == 2
        else pd.NaT
    )

    if pd.isna(start) and pd.isna(end):
        return None
    if pd.isna(start):
        start = end
    if pd.isna(end):
        end = start
    assert not pd.isna(start) and not pd.isna(end)

    lo = min(start, end)
    hi = max(start, end)
    midpoint = lo + (hi - lo) / 2
    year = int(midpoint.year)
    month = int(midpoint.month)
    if year < 1900 or year > 2100:
        return None
    return year, month
