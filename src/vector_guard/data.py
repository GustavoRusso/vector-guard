"""Load raw VectorNet and ENA virus detection tables from local copies."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TypedDict

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


# Tax IDs verified against ENA Portal (tax_tree counts). Spec listed older/alternate
# IDs for CCHFV and Toscana that currently return empty sequence trees in ENA.
VIRUS_VECTOR_TAXON_MAP: tuple[VirusTaxonTarget, ...] = (
    {
        "pathogen": "West Nile virus",
        "tax_ids": (11082,),
        "vector_group": "mosquito",
    },
    {
        "pathogen": "Usutu virus",
        "tax_ids": (64286,),
        "vector_group": "mosquito",
    },
    {
        "pathogen": "Dengue virus",
        "tax_ids": (12637,),
        "vector_group": "mosquito",
    },
    {
        "pathogen": "Chikungunya virus",
        "tax_ids": (37124,),
        "vector_group": "mosquito",
    },
    {
        "pathogen": "Zika virus",
        "tax_ids": (64320,),
        "vector_group": "mosquito",
    },
    {
        "pathogen": "Sindbis virus",
        "tax_ids": (11034,),
        "vector_group": "mosquito",
    },
    {
        "pathogen": "Rift Valley fever virus",
        "tax_ids": (11588,),
        "vector_group": "mosquito",
    },
    {
        "pathogen": "Tick-borne encephalitis virus",
        "tax_ids": (11084,),
        "vector_group": "tick",
    },
    {
        "pathogen": "Crimean-Congo hemorrhagic fever virus",
        "tax_ids": (3052518,),  # Orthonairovirus haemorrhagiae
        "vector_group": "tick",
    },
    {
        "pathogen": "Bluetongue virus",
        "tax_ids": (40051,),
        "vector_group": "biting_midge",
    },
    {
        "pathogen": "Schmallenberg virus",
        "tax_ids": (1133363,),
        "vector_group": "biting_midge",
    },
    {
        "pathogen": "Sandfly fever Naples phlebovirus / Toscana virus",
        "tax_ids": (11590, 206160, 1933189),  # Toscana + Naples complex
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
    return root / "data" / "raw" / "vector"


def default_virus_raw_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "data" / "raw" / "virus"


def resolve_vector_core_path(raw_dir: Path) -> Path:
    """Resolve the DwC-A core table path under *raw_dir* via ``meta.xml``."""
    if not raw_dir.exists():
        raise FileNotFoundError(
            f"Vector raw directory not found: {raw_dir}. "
            "Run notebooks/01_extract_vectors.ipynb first."
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
        "Run notebooks/01_extract_vectors.ipynb to refresh the raw archive."
    )


def resolve_virus_core_path(raw_dir: Path) -> Path:
    """Resolve the ENA virus detections TSV path under *raw_dir*."""
    if not raw_dir.exists():
        raise FileNotFoundError(
            f"Virus raw directory not found: {raw_dir}. "
            "Run notebooks/03_extract_viruses.ipynb first."
        )

    candidate = raw_dir / _VIRUS_TSV_NAME
    if candidate.exists():
        return candidate

    raise FileNotFoundError(
        f"Could not find {_VIRUS_TSV_NAME} under {raw_dir}. "
        "Run notebooks/03_extract_viruses.ipynb to refresh the raw extract."
    )


def load_vector_detections(raw_dir: Path | None = None) -> pd.DataFrame:
    """Load the VectorNet occurrence core table as a string-typed DataFrame.

    Parameters
    ----------
    raw_dir:
        Directory containing the extracted DwC-A. Defaults to
        ``<repo>/data/raw/vector``.
    """
    directory = Path(raw_dir) if raw_dir is not None else default_vector_raw_dir()
    core_path = resolve_vector_core_path(directory)
    return pd.read_csv(core_path, sep="\t", dtype=str, low_memory=False)


def load_virus_detections(raw_dir: Path | None = None) -> pd.DataFrame:
    """Load the ENA / INSDC virus detections TSV as a string-typed DataFrame.

    Parameters
    ----------
    raw_dir:
        Directory containing ``virus_detections.tsv``. Defaults to
        ``<repo>/data/raw/virus``.
    """
    directory = Path(raw_dir) if raw_dir is not None else default_virus_raw_dir()
    core_path = resolve_virus_core_path(directory)
    return pd.read_csv(core_path, sep="\t", dtype=str, keep_default_na=False)
