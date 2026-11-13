"""Load raw VectorNet and multi-source virus detection tables from local copies."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import NotRequired, TypedDict

import pandas as pd

_DWC_NS = {"dwc": "http://rs.tdwg.org/dwc/text/"}
_DWC_LOCATION_XPATH = (
    ".//{http://rs.tdwg.org/dwc/text/}core"
    "/{http://rs.tdwg.org/dwc/text/}files"
    "/{http://rs.tdwg.org/dwc/text/}location"
)
_CORE_FALLBACKS = ("occurrence.txt", "Occurrence.txt", "taxon.txt")
_VIRUS_TSV_NAME = "virus_detections.tsv"


class VirusTaxonTarget(TypedDict):
    pathogen: str
    tax_ids: tuple[int, ...]
    vector_group: str
    legacy_tax_ids: NotRequired[tuple[int, ...]]


# Tax IDs verified against ENA Portal (tax_tree counts, 2026-11).
# ``tax_ids`` prefer ICTV binomial species nodes (supersets of legacy common-name
# IDs). ``legacy_tax_ids`` retain older NCBI nodes for BV-BRC lineage recall.
VIRUS_VECTOR_TAXON_MAP: tuple[VirusTaxonTarget, ...] = (
    # --- mosquito ---
    {
        "pathogen": "West Nile virus",
        "tax_ids": (3048448,),  # Orthoflavivirus nilense
        "legacy_tax_ids": (11082,),
        "vector_group": "mosquito",
    },
    {
        "pathogen": "Usutu virus",
        "tax_ids": (3048443,),  # Orthoflavivirus usutuense
        "legacy_tax_ids": (64286,),
        "vector_group": "mosquito",
    },
    {
        "pathogen": "Dengue virus",
        "tax_ids": (3052464,),  # Orthoflavivirus denguei
        "legacy_tax_ids": (12637,),
        "vector_group": "mosquito",
    },
    {
        "pathogen": "Chikungunya virus",
        "tax_ids": (3426298,),  # Alphavirus chikungunya
        "legacy_tax_ids": (37124,),
        "vector_group": "mosquito",
    },
    {
        "pathogen": "Zika virus",
        "tax_ids": (3048459,),  # Orthoflavivirus zikaense
        "legacy_tax_ids": (64320,),
        "vector_group": "mosquito",
    },
    {
        "pathogen": "Sindbis virus",
        "tax_ids": (3426318,),  # Alphavirus sindbis
        "legacy_tax_ids": (11034,),
        "vector_group": "mosquito",
    },
    {
        "pathogen": "Rift Valley fever virus",
        "tax_ids": (3052676,),  # Phlebovirus riftense
        "legacy_tax_ids": (11588,),
        "vector_group": "mosquito",
    },
    {
        "pathogen": "Batai orthobunyavirus",
        "tax_ids": (3052371,),  # Orthobunyavirus bataiense
        "legacy_tax_ids": (80942,),  # Batai virus
        "vector_group": "mosquito",
    },
    {
        "pathogen": "Tahyna / California encephalitis orthobunyavirus",
        "tax_ids": (3052445, 35305, 178787),  # Tahyna + California encephalitis complex
        "legacy_tax_ids": (45270,),  # Tahyna virus
        "vector_group": "mosquito",
    },
    {
        "pathogen": "Inkoo orthobunyavirus",
        "tax_ids": (45269,),  # Inkoo virus
        "legacy_tax_ids": (),
        "vector_group": "mosquito",
    },
    {
        "pathogen": "Japanese encephalitis virus",
        "tax_ids": (3048158,),  # Orthoflavivirus japonicum
        "legacy_tax_ids": (11072,),
        "vector_group": "mosquito",
    },
    {
        "pathogen": "Yellow fever virus",
        "tax_ids": (3046277,),  # Orthoflavivirus flavi
        "legacy_tax_ids": (11089,),
        "vector_group": "mosquito",
    },
    # --- tick ---
    {
        "pathogen": "Tick-borne encephalitis virus",
        "tax_ids": (3052465,),  # Orthoflavivirus encephalitidis
        "legacy_tax_ids": (11084,),
        "vector_group": "tick",
    },
    {
        "pathogen": "Crimean-Congo hemorrhagic fever virus",
        "tax_ids": (3052518,),  # Orthonairovirus haemorrhagiae
        "legacy_tax_ids": (),
        "vector_group": "tick",
    },
    {
        "pathogen": "Louping ill virus",
        "tax_ids": (3048184,),  # Orthoflavivirus loupingi
        "legacy_tax_ids": (11086,),
        "vector_group": "tick",
    },
    {
        "pathogen": "Omsk hemorrhagic fever virus",
        "tax_ids": (3048233,),  # Orthoflavivirus omskense
        "legacy_tax_ids": (12542,),
        "vector_group": "tick",
    },
    {
        "pathogen": "Thogoto / Bourbon thogotovirus",
        "tax_ids": (11569, 2956523),  # Thogotovirus thogotoense + bourbonense
        "legacy_tax_ids": (1618189,),  # Bourbon virus
        "vector_group": "tick",
    },
    {
        "pathogen": "Jingmen tick virus",
        "tax_ids": (1172985,),
        "legacy_tax_ids": (),
        "vector_group": "tick",
    },
    {
        "pathogen": "Alongshan virus",
        "tax_ids": (2269360,),
        "legacy_tax_ids": (),
        "vector_group": "tick",
    },
    # --- biting_midge ---
    {
        "pathogen": "Bluetongue virus",
        "tax_ids": (3431240,),  # Orbivirus caerulinguae
        "legacy_tax_ids": (40051,),
        "vector_group": "biting_midge",
    },
    {
        "pathogen": "Schmallenberg virus",
        "tax_ids": (3052437,),  # Orthobunyavirus schmallenbergense
        "legacy_tax_ids": (1133363,),
        "vector_group": "biting_midge",
    },
    {
        "pathogen": "Epizootic hemorrhagic disease virus",
        "tax_ids": (40054,),
        "legacy_tax_ids": (),
        "vector_group": "biting_midge",
    },
    {
        "pathogen": "African horse sickness virus",
        "tax_ids": (40050,),  # Orbivirus alphaequi
        "legacy_tax_ids": (),
        "vector_group": "biting_midge",
    },
    {
        "pathogen": "Akabane orthobunyavirus",
        "tax_ids": (1933178,),  # Orthobunyavirus akabaneense
        "legacy_tax_ids": (70566,),  # Akabane virus
        "vector_group": "biting_midge",
    },
    # --- sandfly ---
    {
        "pathogen": "Sandfly fever Naples phlebovirus / Toscana virus",
        "tax_ids": (3052686, 3052666, 1933189),  # Toscana + Naples complex
        "legacy_tax_ids": (11590, 206160),
        "vector_group": "sandfly",
    },
    {
        "pathogen": "Phlebovirus (Mediterranean sandfly fever complex)",
        "tax_ids": (3052681, 3052661, 3052675, 904668),  # Sicilian, Massilia, Punique, Granada
        "legacy_tax_ids": (28292,),  # sandfly fever Sicilian virus
        "vector_group": "sandfly",
    },
)


def find_repo_root(start: Path | None = None) -> Path:
    """Walk upward from *start* (or cwd) until ``pyproject.toml`` is found."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise FileNotFoundError(
        f"Could not locate repository root (pyproject.toml) from {current}"
    )


def default_vector_raw_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "data" / "01_raw" / "vector"


def default_virus_raw_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "data" / "01_raw" / "virus"


def default_reference_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "data" / "external"


def default_interim_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "data" / "02_interim"


def default_processed_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "data" / "03_processed"


def resolve_vector_core_path(raw_dir: Path) -> Path:
    """Resolve the DwC-A core table path under *raw_dir* via ``meta.xml``."""
    if not raw_dir.exists():
        raise FileNotFoundError(
            f"Vector raw directory not found: {raw_dir}. "
            "Run notebooks/01_sources/01_extract_vectors.ipynb first."
        )

    meta_path = raw_dir / "meta.xml"
    if meta_path.exists():
        root = ET.parse(meta_path).getroot()
        location = root.find(".//dwc:core/dwc:files/dwc:location", _DWC_NS)
        if location is None:
            location = root.find(_DWC_LOCATION_XPATH)
        if location is None:
            location = root.find(".//core/files/location")
        if location is not None and (location.text or "").strip():
            candidate = raw_dir / location.text.strip()
            if candidate.exists():
                return candidate

    for name in _CORE_FALLBACKS:
        candidate = raw_dir / name
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        f"Could not find DwC-A core table under {raw_dir}. "
        "Run notebooks/01_sources/01_extract_vectors.ipynb to refresh the raw archive."
    )


def resolve_virus_core_path(raw_dir: Path) -> Path:
    """Resolve the unified virus detections TSV path under *raw_dir*."""
    if not raw_dir.exists():
        raise FileNotFoundError(
            f"Virus raw directory not found: {raw_dir}. "
            "Run notebooks/01_sources/03_extract_viruses.ipynb first."
        )

    candidate = raw_dir / _VIRUS_TSV_NAME
    if candidate.exists():
        return candidate

    raise FileNotFoundError(
        f"Could not find {_VIRUS_TSV_NAME} under {raw_dir}. "
        "Run notebooks/01_sources/03_extract_viruses.ipynb to refresh the raw extract."
    )


def load_vector_detections(raw_dir: Path | None = None) -> pd.DataFrame:
    """Load the VectorNet occurrence core table as a string-typed DataFrame.

    Parameters
    ----------
    raw_dir:
        Directory containing the extracted DwC-A. Defaults to
        ``<repo>/data/01_raw/vector``.
    """
    directory = Path(raw_dir) if raw_dir is not None else default_vector_raw_dir()
    core_path = resolve_vector_core_path(directory)
    return pd.read_csv(core_path, sep="\t", dtype=str, low_memory=False)


def load_virus_detections(raw_dir: Path | None = None) -> pd.DataFrame:
    """Load the multi-source virus detections TSV as a string-typed DataFrame.

    Expects the unified schema written by
    ``notebooks/01_sources/03_extract_viruses.ipynb``
    (see ``VIRUS_RAW_COLUMNS`` in ``vector_guard.virus_extract``): ``record_id``,
    ``source``, accessions, pathogen tags, place / NUTS / coords, ``coord_source``,
    and collection / host fields.

    Parameters
    ----------
    raw_dir:
        Directory containing ``virus_detections.tsv``. Defaults to
        ``<repo>/data/01_raw/virus``.
    """
    directory = Path(raw_dir) if raw_dir is not None else default_virus_raw_dir()
    core_path = resolve_virus_core_path(directory)
    return pd.read_csv(core_path, sep="\t", dtype=str, keep_default_na=False)
