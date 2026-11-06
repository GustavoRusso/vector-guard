"""Load raw VectorNet occurrence data from the local DwC-A copy."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

_DWC_NS = {"dwc": "http://rs.tdwg.org/dwc/text/"}
_DWC_LOCATION_XPATH = (
    ".//{http://rs.tdwg.org/dwc/text/}core"
    "/{http://rs.tdwg.org/dwc/text/}files"
    "/{http://rs.tdwg.org/dwc/text/}location"
)
_CORE_FALLBACKS = ("occurrence.txt", "Occurrence.txt", "taxon.txt")


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
