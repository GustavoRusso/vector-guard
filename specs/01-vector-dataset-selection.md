# Vector dataset selection

The project use the **VectorNet** Darwin Core Archive (DwC-A) published by ECDC / EFSA on the GBIF Integrated Publishing Toolkit (IPT) as the sole primary vector detection dataset.

| Field | Value |
|-------|-------|
| Dataset | [VectorNet](https://ipt.gbif.org/resource?r=vndatabase) (ECDC / EFSA) |
| Resource key | `vndatabase` |
| GBIF dataset UUID | `e497586a-1bdf-4f69-90eb-645d615762c8` |
| Latest download URL | `https://ipt.gbif.org/archive.do?r=vndatabase` |
| Format | Darwin Core Archive (DwC-A ZIP) |
| License | [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Local path | `data/raw/vector/` (not committed; re-fetched on demand) |
| Extract notebook | [`notebooks/01_extract_vectors.ipynb`](../notebooks/01_extract_vectors.ipynb) |
| Loader | [`src/vector_guard/data.py`](../src/vector_guard/data.py) — `load_vector_detections()` |

## Requirements that drove the choice

Vector Guard needs occurrence-like records that can be joined later to virus detections on space and time:

1. **Taxon / species** identifiable at least to genus or species within the medical and veterinary vector groups of interest.
2. **Geographic location** with reusable keys (coordinates and/or administrative codes) covering **Europe** (Mediterranean basin acceptable).
3. **Detection time** (`eventDate` or equivalent).
4. **Free access** with a **reproducible download** that does not require a logged-in user account when possible.
5. Preference for **surveillance / expert-validated** data over mixed citizen-science dumps.

## Selected source: VectorNet DwC-A

### What it provides

VectorNet is the joint ECDC / EFSA network database on the presence and distribution of disease vectors across Europe and the Mediterranean basin. The IPT DwC-A exposes that database as a single occurrence table plus metadata.

Coverage relevant to this project:

- **Geographic:** Europe and the Mediterranean basin.
- **Temporal:** roughly 1980–present (archive metadata; exact span depends on the refresh).
- **Taxonomic groups:** mosquitoes (`Culicidae`), ticks (`Ixodida`), biting midges (`Ceratopogonidae` / `Culicoides`), sandflies (`Phlebotominae`).
- **Volume:** on the order of ~277k occurrence rows in the local extract used during project setup.

Core fields used (or expected) for modelling and joins:

| Concept | DwC-A / table fields |
|---------|----------------------|
| Identity | `occurrenceID`, `id` |
| Taxon | `scientificName`, `verbatimIdentification` |
| Place | `decimalLatitude`, `decimalLongitude`, `countryCode`, `higherGeographyID` (often NUTS3/GAUL), `higherGeography` |
| Time | `eventDate` |
| Effort / status | `samplingProtocol`, `sampleSizeValue`, `sampleSizeUnit`, `individualCount`, `degreeOfEstablishment`, `lifeStage` |
| Optional pathogen note | `dynamicProperties` (sparse JSON, e.g. `{"pathogen": "West Nile virus"}`) |

Archive layout after extract: `occurrence.txt` (core table), `meta.xml`, `eml.xml`, plus `manifest.json` written by the extract notebook (fetch time, URL, SHA-256, citation).

### Why VectorNet was chosen

- **Institutional fit:** Official ECDC / EFSA One Health vector surveillance, aligned with European public-health use cases described in early research notes under `docs/`.
- **Schema fit:** Standardized DwC-A with coordinates, country codes, administrative geography IDs, and event dates—enough to support country-, NUTS-, or grid-level aggregation later.
- **Access model:** One HTTP GET of the latest ZIP; **no GBIF account**, no async download queue, no API key.
- **Surveillance semantics:** Includes sampling protocol / effort fields and establishment / presence–absence style signals, not only opportunistic presence points.

### How to refresh

Run all cells in [`notebooks/01_extract_vectors.ipynb`](../notebooks/01_extract_vectors.ipynb). The notebook wipes `data/raw/vector/` (except `.gitkeep`), downloads the latest IPT archive, extracts it, and writes `manifest.json`.

```python
from vector_guard.data import load_vector_detections

df = load_vector_detections()
```

## Candidates for future additions

Sources below are **not** part of the primary vector table. They may be joined later if geographic or pathogen coverage needs it.

### SPVECTORSURV (Spain tick and mosquito monitoring)

- **What:** [SPVECTORSURV](https://www.gbif.org/dataset/fc1dd9e3-ff53-4d57-9d8e-e29afbb955b8) — *Monitoring competent vectors of Crimea Congo Haemorragic Fever (ticks), West Nile and Rift Valley Fever in Spain (mosquitos)* (Ministerio de Agricultura, Pesca y Alimentación; DOI [10.15470/fn1bet](https://doi.org/10.15470/fn1bet)). Occurrence Darwin Core Archive on the Spanish GBIF IPT ([`r=spvectorsurv`](https://ipt.gbif.es/resource?r=spvectorsurv)).
- **GBIF dataset UUID:** `fc1dd9e3-ff53-4d57-9d8e-e29afbb955b8`
- **Latest download URL:** `https://ipt.gbif.es/archive.do?r=spvectorsurv`
- **License:** [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)
- **Coverage:** Spain (southern mainland via IREC; Balearic Islands via the University of the Balearic Islands). Version 1.5 (published 2026-07-03) holds on the order of ~2.6k occurrences, currently tick sampling from 2024. The project window is January 2024–December 2026; mosquito surveillance for West Nile and Rift Valley fever is in scope and expected in later releases. Sampling follows a predefined protocol and is published in Darwin Core aligned with VectorNet.
- **Why a candidate, not the primary source:** Expert One Health surveillance (EU4Health, EFSA-coordinated) aimed at competent vectors of Crimean–Congo haemorrhagic fever, West Nile, and Rift Valley fever. It can densify Spanish tick detections, and later mosquito detections, on top of VectorNet. It does not replace VectorNet: geography is Spain only, the current extract is small and tick-only, the series is still being filled through 2026, and the license is non-commercial (CC BY-NC 4.0), which is stricter than VectorNet’s CC BY 4.0.

## Discarded alternatives

The options below were considered during early research and **not** selected as the primary vector source.

### GBIF SQL Data Cubes / full occurrence dumps

- **What:** GBIF occurrence warehouse queries and [data cubes](https://techdocs.gbif.org/en/data-use/data-cubes) over global occurrences (SQL-style extracts across many datasets).
- **Why discarded:** Asynchronous download jobs typically need **GBIF user credentials**; queues can take minutes; results mix many publishers and citizen-science observations without VectorNet’s surveillance protocols or consistent absence/effort metadata. Too heavy and too noisy for a Europe-focused vector–virus risk pipeline when VectorNet already publishes a curated DwC-A.

### Older / static VectorNet GBIF snapshot and map portals

- **What:** The GBIF dataset page snapshot referenced in early notes ([`4abd984b-122c-44a0-8c92-b37e2f5299b1`](https://www.gbif.org/dataset/4abd984b-122c-44a0-8c92-b37e2f5299b1)); ECDC / VectorNet **static distribution map** portals and PNG/PDF map products; the [VectorNet data portal](https://www.vectornetdata.org/) as a browse UI.
- **Why discarded:** Maps and portal views are useful for human inspection but are a poor reproducible training input (manual export, image or aggregated polygons, not a stable tabular refresh). Prefer the **live IPT DwC-A** (`r=vndatabase`, UUID `e497586a-1bdf-4f69-90eb-645d615762c8`) for point/admin-level tabular occurrences and checksummed refreshes.

### VectorByte (`VecDyn` / `VecTraits`)

- **What:** Vector ecology data ecosystem ([VectorByte](https://www.vectorbyte.org/blog/welcome-to-the-vector-data-ecosystem))—`VecTraits` (trait / experimental data) and `VecDyn` (population / abundance time series).
- **Why discarded as primary source:** `VecTraits` is oriented to laboratory traits (e.g. thermal response), not Europe-wide surveillance occurrences. `VecDyn` coverage is fragmented relative to the unified ECDC/EFSA VectorNet database for EU/Mediterranean administrative geography. May remain useful later as **auxiliary features**, not as the main vector detection table.

