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


def load_pathogen_vector_group(reference_dir: Path | None = None) -> pd.DataFrame:
    """Load ``data/external/pathogen_vector_group.csv`` (mirror of ``VIRUS_VECTOR_TAXON_MAP``)."""
    directory = Path(reference_dir) if reference_dir is not None else default_reference_dir()
    path = directory / "pathogen_vector_group.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run notebooks/01_sources/06_reference_vector_groups.ipynb first."
        )
    return pd.read_csv(
        path,
        dtype={"pathogen_name": str, "vector_group": str},
    )


def load_priority_vector_taxa(reference_dir: Path | None = None) -> pd.DataFrame:
    """Load ``data/external/priority_vector_taxa.csv`` (EDA / prep closed species features).

    Locked modelling contract: after the unit-grain species pivot, ``FEATURE_COLS``
    use exactly these taxa as ``vector_count_<feature_slug>`` (0 if absent). Do not
    substitute a frequency-selected column set for the modelling handoff.
    """
    directory = Path(reference_dir) if reference_dir is not None else default_reference_dir()
    path = directory / "priority_vector_taxa.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run notebooks/01_sources/06_reference_vector_groups.ipynb first."
        )
    return pd.read_csv(
        path,
        dtype={
            "scientific_name": str,
            "vector_group": str,
            "feature_slug": str,
            "notes": str,
        },
    )


def feature_slug_from_scientific_name(scientific_name: object) -> str:
    """Stable snake_case slug for ``vector_count_<slug>`` modelling feature columns."""
    text = _clean_text(scientific_name).casefold()
    if not text:
        return ""
    slug = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", slug).strip("_")


_PARENTHETICAL_RE = re.compile(r"\([^)]*\)")
_YEAR_TOKEN_RE = re.compile(r"^\d{4}$")


def _strip_scientific_name_authorship(name: str) -> str:
    """Keep genus + lowercase epithets; drop author / year tokens."""
    tokens = re.sub(r"\s+", " ", name).strip().split()
    if not tokens:
        return ""
    kept = [tokens[0]]
    for tok in tokens[1:]:
        cleaned = tok.strip(",")
        if not cleaned:
            continue
        if _YEAR_TOKEN_RE.fullmatch(cleaned):
            break
        # Species / infra-specific epithets are lowercase; authors are capitalized.
        if cleaned[0].isupper():
            break
        kept.append(cleaned)
    return " ".join(kept)


def scientific_name_lookup_candidates(scientific_name: object) -> list[str]:
    """Ordered unique keys for ``vector_taxon_groups.csv`` lookup.

    Ladder (spec ``04`` / SPVECTORSURV authored names):

    1. Exact cleaned string
    2. Parenthetical subgenus / clutter removed
    3. Authorship / year stripped (binomial / trinomial bare name)
    4. Genus-only token (CSV genus-level row fallback)
    """
    raw = _clean_text(scientific_name)
    if not raw:
        return []

    candidates: list[str] = []

    def _add(value: str) -> None:
        text = re.sub(r"\s+", " ", value).strip(" ,;")
        if text and text not in candidates:
            candidates.append(text)

    _add(raw)
    no_paren = _PARENTHETICAL_RE.sub(" ", raw)
    _add(no_paren)
    bare = _strip_scientific_name_authorship(no_paren)
    _add(bare)
    genus = bare.split()[0] if bare else ""
    _add(genus)
    return candidates


def resolve_vector_group(
    scientific_name: object,
    taxon_map: Mapping[str, str],
) -> str:
    """Map a published ``scientificName`` to ``vector_group`` via the lookup ladder.

    Prefers an exact map hit, then normalized candidates, then a genus-only CSV
    key when present. Returns ``\"\"`` when unmapped.
    """
    for candidate in scientific_name_lookup_candidates(scientific_name):
        hit = taxon_map.get(candidate)
        if hit:
            return str(hit)
    return ""


# ---------------------------------------------------------------------------
# Virus host → host_group (spec ``04``; interim only; merge does not consume)
# ---------------------------------------------------------------------------

HOST_GROUPS: tuple[str, ...] = (
    "mosquito",
    "tick",
    "biting_midge",
    "sandfly",
    "human",
    "livestock",
    "bird",
    "wildlife_mammal",
    "lab",
    "unknown",
)

# Lower value = preferred when multi-segment host strings disagree.
HOST_GROUP_PRIORITY: dict[str, int] = {
    "mosquito": 0,
    "tick": 0,
    "biting_midge": 0,
    "sandfly": 0,
    "bird": 1,
    "wildlife_mammal": 2,
    "livestock": 3,
    "human": 4,
    "lab": 5,
    "unknown": 6,
}

# Casefolded genus / higher-taxon → vector_group. VectorNet genera plus global
# non-EU genera and family/order names seen in virus host strings.
GLOBAL_VECTOR_GENUS_TO_GROUP: dict[str, str] = {
    # Mosquitoes (Culicidae) — VectorNet + global
    "aedes": "mosquito",
    "anopheles": "mosquito",
    "coquillettidia": "mosquito",
    "culex": "mosquito",
    "culiseta": "mosquito",
    "orthopodomyia": "mosquito",
    "uranotaenia": "mosquito",
    "ochlerotatus": "mosquito",
    "mansonia": "mosquito",
    "armigeres": "mosquito",
    "psorophora": "mosquito",
    "toxorhynchites": "mosquito",
    "haemagogus": "mosquito",
    "culicidae": "mosquito",
    # Ticks (Ixodida) — VectorNet + global
    "dermacentor": "tick",
    "hyalomma": "tick",
    "ixodes": "tick",
    "ornithodoros": "tick",
    "rhipicephalus": "tick",
    "haemaphysalis": "tick",
    "amblyomma": "tick",
    "argas": "tick",
    "boophilus": "tick",
    "ixodoidea": "tick",
    "ixodida": "tick",
    "ixodidae": "tick",
    # Biting midges
    "culicoides": "biting_midge",
    "ceratopogonidae": "biting_midge",
    # Sandflies
    "phlebotomus": "sandfly",
    "sergentomyia": "sandfly",
    "lutzomyia": "sandfly",
    "phlebotominae": "sandfly",
    "psychodidae": "sandfly",
}

_HOST_PLACEHOLDERS: frozenset[str] = frozenset(
    {
        "",
        "missing",
        "unknown",
        "na",
        "n/a",
        "none",
        "null",
        "nan",
        "not applicable",
        "not collected",
        "no_value",
        "<na>",
    }
)

_HOST_COUNT_SUFFIX_RE = re.compile(r":\d+\s*$")
_HOST_SEGMENT_SPLIT_RE = re.compile(r"[|;]")

# Lab / culture markers — checked before arthropod genus matching.
_HOST_LAB_RE = re.compile(
    r"(?i)\b("
    r"vero(?:[-\s]?e?6)?|"
    r"c6\s*/?\s*36|"
    r"bhk(?:[-\s]?21)?|"
    r"bsr|"
    r"ap\s*61|"
    r"cell[\s_-]?line|"
    r"cell[\s_-]?culture|"
    r"cells?|"
    r"cdna\s+clone|"
    r"clone|"
    r"vaccine|"
    r"cultured\s+virus|"
    r"laboratory\s+tissue\s+culture|"
    r"supernatant"
    r")\b"
)

_HOST_HUMAN_RE = re.compile(
    r"(?i)\b(homo\s+sapiens|human|patient|homo)\b"
)
_HOST_BIRD_RE = re.compile(
    r"(?i)\b("
    r"bird|avian|aves|poultry|chicken|duck|goose|swan|crow|raven|magpie|"
    r"jay|sparrow|thrush|pigeon|dove|gull|owl|eagle|hawk|falcon|vulture|"
    r"corvus|coloeus|turdus|larus|anas|gallus|passer|pica|cyanocitta|"
    r"buteo|strix|pelecanus|accipitridae|strigiformes|passeriformes|"
    r"bird_outbreaks|unspecified\s+bird"
    r")\b"
)
_HOST_LIVESTOCK_RE = re.compile(
    r"(?i)\b("
    r"cattle|bovine|bos\s+taurus|cow|ox|buffalo|"
    r"sheep|ovine|ovis\s+aries|"
    r"goat|caprine|capra|"
    r"horse|equine|equus|equidae|equid|"
    r"pig|swine|porcine|sus\s+scrofa|"
    r"camel|camelid|llama|alpaca|"
    r"dog|canine|canis\s+lupus\s+fam(?:il)?iaris|canis\s+familiaris|"
    r"cat|feline|felis\s+catus|"
    r"domestic|livestock|ruminant|"
    r"equid_outbreaks|goat/sheep|small\s+ruminant|"
    r"unspecified\s+mammal"
    r")\b"
)
_HOST_WILD_MAMMAL_RE = re.compile(
    r"(?i)\b("
    r"deer|odocoileus|cervid|cervus|mule\s+deer|white[-\s]?tailed|"
    r"rodent|mouse|mus\s+musculus|rattus|rat|squirrel|sciurus|"
    r"bat|chiroptera|"
    r"boar|wild\s+boar|"
    r"primate|alouatta|macaca|monkey|"
    r"fox|vulpes|wolf|canis\s+lupus(?!\s+fam)|coyote|canis\s+latrans|"
    r"hare|lepus|rabbit|oryctolagus|"
    r"hedgehog|erinaceus|shrew|wildlife"
    r")\b"
)
_HOST_DOMESTIC_PREFIX_RE = re.compile(r"(?i)^\s*domestic\s*-")
_HOST_WILD_PREFIX_RE = re.compile(r"(?i)^\s*wild\s*-")

_HOST_ENGLISH_VECTOR_RE = re.compile(
    r"(?i)\b("
    r"mosquito(?:es)?|tick(?:s)?|biting\s+midge(?:s)?|midge(?:s)?|"
    r"sand\s*-?\s*fl(?:y|ies)|sandfly|sandflies|vector"
    r")\b"
)
_HOST_ENGLISH_VECTOR_TO_GROUP: dict[str, str] = {
    "mosquito": "mosquito",
    "mosquitoes": "mosquito",
    "tick": "tick",
    "ticks": "tick",
    "midge": "biting_midge",
    "midges": "biting_midge",
    "biting midge": "biting_midge",
    "biting midges": "biting_midge",
    "sandfly": "sandfly",
    "sandflies": "sandfly",
    "sand fly": "sandfly",
    "sand flies": "sandfly",
    "sand-fly": "sandfly",
    "sand-flies": "sandfly",
}

# isolation_source fallbacks (applied only when host → unknown)
_ISO_LAB_RE = re.compile(
    r"(?i)\b("
    r"vero|c6\s*/?\s*36|bhk|ap\s*61|cell[\s_-]?line|cell[\s_-]?culture|"
    r"cultured\s+virus|laboratory\s+tissue\s+culture|vaccine|passage|"
    r"supernatant|clone"
    r")\b"
)
_ISO_MOSQUITO_RE = re.compile(
    r"(?i)\b("
    r"mosquito\s+pool|pooled\s+(?:blended\s+)?mosquitoes|whole\s+mosquito|"
    r"mosquito\s+homogenate|mosquitoes?\b"
    r")"
)
_ISO_TICK_RE = re.compile(
    r"(?i)\b("
    r"tick\s+pool|ticks?\b|i\.?\s*persulcatus|ixodes|hyalomma|"
    r"dermacentor|rhipicephalus|haemaphysalis|amblyomma"
    r")"
)
_ISO_MIDGE_RE = re.compile(r"(?i)\bculicoides\b")
_ISO_SANDFLY_RE = re.compile(r"(?i)\b(sand\s*-?\s*fl(?:y|ies)|phlebotomus|lutzomyia)\b")
_ISO_HUMAN_RE = re.compile(
    r"(?i)\b(patient|human\s+(?:blood|serum|plasma)|human)\b"
)
_ISO_LIVESTOCK_RE = re.compile(
    r"(?i)\b(bovine|ovine|caprine|equine|swine|cattle|sheep|goat|horse|pig)\b"
)


def load_host_groups(reference_dir: Path | None = None) -> pd.DataFrame:
    """Load ``data/external/host_groups.csv`` (virus host → ``host_group`` aliases)."""
    directory = Path(reference_dir) if reference_dir is not None else default_reference_dir()
    path = directory / "host_groups.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run notebooks/01_sources/06b_reference_host_groups.ipynb first."
        )
    return pd.read_csv(
        path,
        dtype={"host_key": str, "host_group": str, "notes": str},
        keep_default_na=False,
    )


def build_host_alias_map(host_groups_df: pd.DataFrame) -> dict[str, str]:
    """Map ``norm_key(host_key)`` → ``host_group`` from the curated reference CSV.

    Rejects empty keys, ``unknown`` targets, and values outside ``HOST_GROUPS``.
    Duplicate normalized keys with conflicting groups raise ``ValueError``.
    """
    if "host_key" not in host_groups_df.columns or "host_group" not in host_groups_df.columns:
        raise ValueError("host_groups_df must have columns host_key, host_group")

    allowed = set(HOST_GROUPS) - {"unknown"}
    mapping: dict[str, str] = {}
    for row in host_groups_df.itertuples(index=False):
        key = norm_key(getattr(row, "host_key", ""))
        group = _clean_text(getattr(row, "host_group", "")).casefold()
        if not key:
            raise ValueError("host_groups.csv has an empty host_key after normalization")
        if group not in allowed:
            raise ValueError(
                f"Invalid host_group {group!r} for host_key {key!r}; "
                f"expected one of {sorted(allowed)}"
            )
        existing = mapping.get(key)
        if existing is not None and existing != group:
            raise ValueError(
                f"Conflicting host_group for key {key!r}: {existing!r} vs {group!r}"
            )
        mapping[key] = group
    return mapping


def build_host_taxon_lookup(
    vector_taxon_df: pd.DataFrame | None = None,
) -> dict[str, str]:
    """Casefolded scientific_name / genus → arthropod ``host_group``.

    Starts from ``GLOBAL_VECTOR_GENUS_TO_GROUP`` and overlays VectorNet
    ``vector_taxon_groups.csv`` scientific names (and their genus tokens).
    """
    mapping: dict[str, str] = dict(GLOBAL_VECTOR_GENUS_TO_GROUP)
    if vector_taxon_df is None:
        return mapping
    if "scientific_name" not in vector_taxon_df.columns or "vector_group" not in vector_taxon_df.columns:
        raise ValueError("vector_taxon_df must have columns scientific_name, vector_group")
    allowed = {"mosquito", "tick", "biting_midge", "sandfly"}
    for row in vector_taxon_df.itertuples(index=False):
        name = _clean_text(getattr(row, "scientific_name", ""))
        group = _clean_text(getattr(row, "vector_group", "")).casefold()
        if not name or group not in allowed:
            continue
        mapping[name.casefold()] = group
        genus = name.split()[0].casefold() if name.split() else ""
        if genus:
            mapping.setdefault(genus, group)
    return mapping


def _is_host_placeholder(text: str) -> bool:
    return text.casefold().strip() in _HOST_PLACEHOLDERS


def _split_host_segments(host: object) -> list[str]:
    """Split multi-host strings and strip outbreak ``:count`` suffixes."""
    raw = _clean_text(host)
    if not raw or _is_host_placeholder(raw):
        return []
    segments: list[str] = []
    for part in _HOST_SEGMENT_SPLIT_RE.split(raw):
        segment = _HOST_COUNT_SUFFIX_RE.sub("", part).strip(" ,/-")
        if not segment or _is_host_placeholder(segment):
            continue
        segments.append(segment)
    return segments


def _match_english_vector(text: str) -> str:
    match = _HOST_ENGLISH_VECTOR_RE.search(text)
    if not match:
        return ""
    token = match.group(0).casefold().replace("-", " ")
    token = re.sub(r"\s+", " ", token).strip()
    if token == "vector":
        return ""
    return _HOST_ENGLISH_VECTOR_TO_GROUP.get(token, "")


def _match_arthropod_taxon(text: str, taxon_to_group: Mapping[str, str]) -> str:
    # Normalize dotted genera (e.g. Amblyomma.javanense) and collapse spaces.
    cleaned = re.sub(r"\.", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return ""
    folded = cleaned.casefold()
    if folded in taxon_to_group:
        return taxon_to_group[folded]
    # Full binomial / trinomial progressive prefixes.
    tokens = folded.split()
    for n in range(len(tokens), 0, -1):
        candidate = " ".join(tokens[:n])
        hit = taxon_to_group.get(candidate)
        if hit:
            return hit
    # Abbreviated binomial: "I. persulcatus" / "I.persulcatus"
    abbrev = re.match(r"^([a-z])\.?\s+([a-z]+)$", folded)
    if abbrev:
        species = abbrev.group(2)
        for key, group in taxon_to_group.items():
            parts = key.split()
            if len(parts) >= 2 and parts[0].startswith(abbrev.group(1)) and parts[1] == species:
                return group
    return _match_english_vector(cleaned)


def _classify_host_segment(
    segment: str,
    *,
    host_alias_map: Mapping[str, str],
    taxon_to_group: Mapping[str, str],
) -> str:
    """Classify one cleaned host segment; never returns empty (uses ``unknown``)."""
    if not segment or _is_host_placeholder(segment):
        return "unknown"

    # 1. Curated alias table
    alias_hit = host_alias_map.get(norm_key(segment))
    if alias_hit:
        return alias_hit

    # Outbreak token shortcuts after :count strip (human, bird_outbreaks, …)
    folded = segment.casefold().strip()
    if folded in {"human", "homo sapiens", "homo"}:
        return "human"
    if folded.startswith("bird_outbreak") or folded in {"bird", "avian"}:
        return "bird"
    if folded.startswith("equid_outbreak") or folded.startswith("equine"):
        return "livestock"

    # 2. Lab / culture guard (before taxon prefix match)
    if _HOST_LAB_RE.search(segment):
        return "lab"

    # 3. Arthropod taxon / English vector term
    arthropod = _match_arthropod_taxon(segment, taxon_to_group)
    if arthropod:
        return arthropod

    # 4. Vertebrate cues (avian before Wild -/Domestic -; Wild - before livestock keywords)
    if _HOST_HUMAN_RE.search(segment):
        return "human"
    if _HOST_BIRD_RE.search(segment):
        return "bird"
    if _HOST_WILD_PREFIX_RE.search(segment):
        return "wildlife_mammal"
    if _HOST_DOMESTIC_PREFIX_RE.search(segment) or _HOST_LIVESTOCK_RE.search(segment):
        return "livestock"
    if _HOST_WILD_MAMMAL_RE.search(segment):
        return "wildlife_mammal"

    return "unknown"


def _classify_isolation_source(isolation_source: object) -> str:
    """Fallback classifier for raw ``isolation_source`` when host is unresolved."""
    text = _clean_text(isolation_source)
    if not text or _is_host_placeholder(text):
        return "unknown"
    if _ISO_LAB_RE.search(text):
        return "lab"
    if _ISO_MOSQUITO_RE.search(text):
        return "mosquito"
    if _ISO_TICK_RE.search(text):
        return "tick"
    if _ISO_MIDGE_RE.search(text):
        return "biting_midge"
    if _ISO_SANDFLY_RE.search(text):
        return "sandfly"
    if _ISO_HUMAN_RE.search(text):
        return "human"
    if _ISO_LIVESTOCK_RE.search(text):
        return "livestock"
    return "unknown"


def _pick_host_group(groups: list[str]) -> str:
    """Pick one ``host_group`` by ``HOST_GROUP_PRIORITY`` (lower wins)."""
    if not groups:
        return "unknown"
    return min(groups, key=lambda g: HOST_GROUP_PRIORITY.get(g, 99))


def classify_host_group(
    host: object,
    *,
    host_alias_map: Mapping[str, str],
    taxon_to_group: Mapping[str, str] | None = None,
    isolation_source: object = "",
) -> str:
    """Classify free-text virus ``host`` into a locked ``host_group`` value.

    Implements the segment ladder, multi-host priority tie-break, and
    ``isolation_source`` fallback from spec ``04``. Never overrides a resolved
    host with isolation_source (clinical hosts passaged in cells stay vertebrate).
    """
    taxa = taxon_to_group if taxon_to_group is not None else GLOBAL_VECTOR_GENUS_TO_GROUP
    segments = _split_host_segments(host)
    if segments:
        groups = [
            _classify_host_segment(
                segment,
                host_alias_map=host_alias_map,
                taxon_to_group=taxa,
            )
            for segment in segments
        ]
        picked = _pick_host_group(groups)
        if picked != "unknown":
            return picked

    # Host blank / unresolved → isolation_source fallback
    return _classify_isolation_source(isolation_source)


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
