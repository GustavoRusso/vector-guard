# Vector dataset selection

The project uses the **VectorNet observations** Darwin Core Archive (DwC-A) published by ECDC / EFSA via the official VectorNet GBIF publisher (IPT hosted by GBIF Sweden) as the sole primary vector detection dataset.

| Field | Value |
|-------|-------|
| Dataset | [VectorNet observations](https://www.gbif.org/dataset/4abd984b-122c-44a0-8c92-b37e2f5299b1) (ECDC / EFSA) |
| Resource key | `vectornet_historical_data` |
| GBIF dataset UUID | `4abd984b-122c-44a0-8c92-b37e2f5299b1` |
| DOI | [10.15468/f3k8r9](https://doi.org/10.15468/f3k8r9) |
| Latest download URL | `https://www.gbif.se/ipt/archive.do?r=vectornet_historical_data` |
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

## Selected source: VectorNet observations DwC-A

### What it provides

VectorNet is the joint ECDC / EFSA network database on the presence and distribution of disease vectors across Europe and the Mediterranean basin. The official **VectorNet observations** IPT DwC-A exposes that database as a single occurrence table plus metadata, registered under the VectorNet GBIF publisher (endorsed by GBIF Sweden) and surfaced on the [VectorNet Data Portal](https://www.vectornetdata.org/).

Coverage relevant to this project:

- **Geographic:** Europe and the Mediterranean basin.
- **Temporal:** roughly 1980–mid-2025 (archive metadata; exact span depends on the refresh).
- **Taxonomic groups:** mosquitoes (`Culicidae`), ticks (`Ixodida`), biting midges (`Ceratopogonidae` / `Culicoides`), sandflies (`Phlebotominae`).
- **Volume:** on the order of ~120k occurrence rows in the published archive.

Core fields used (or expected) for modelling and joins:

| Concept | DwC-A / table fields |
|---------|----------------------|
| Identity | `occurrenceID`, `id` |
| Taxon | `scientificName`, `verbatimIdentification`, `identificationRemarks` |
| Place | `decimalLatitude`, `decimalLongitude`, `higherGeographyID` (often NUTS/GAUL), `locationAccordingTo` |
| Time | `eventDate` |
| Effort | `samplingProtocol`, `sampleSizeValue`, `sampleSizeUnit`, `individualCount`, `lifeStage` |
| Provenance | `bibliographicCitation`, `basisOfRecord`, `associatedTaxa` |

Country is typically derived from the `higherGeographyID` prefix (NUTS/GAUL codes) rather than a dedicated `countryCode` column. The observations archive does **not** include `degreeOfEstablishment`, `occurrenceStatus`, `higherGeography`, or `dynamicProperties` as published columns.

Archive layout after extract: `occurrence.txt` (core table), `meta.xml`, `eml.xml`, plus `manifest.json` written by the extract notebook (fetch time, URL, SHA-256, citation).

### Why VectorNet observations was chosen

- **Institutional fit:** Official ECDC / EFSA One Health vector surveillance under the VectorNet GBIF publisher, aligned with European public-health use cases described in early research notes under `docs/`.
- **Schema fit:** Standardized DwC-A with coordinates, administrative geography IDs, and event dates—enough to support country-, NUTS-, or grid-level aggregation later.
- **Access model:** One HTTP GET of the latest ZIP from the GBIF Sweden IPT; **no GBIF account**, no async download queue, no API key.
- **Surveillance semantics:** Includes sampling protocol / effort fields, not only opportunistic presence points.
- **Publisher status:** Live registration on GBIF.org with DOI `10.15468/f3k8r9`, rather than a parallel Training Organization IPT resource.

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

### VectorDistributionStatus (admin-unit establishment snapshots)

- **What:** Expert establishment / presence–absence status by NUTS or GAUL unit, published as versioned DwC-A snapshots (e.g. [VectorDistributionStatus_2026](https://www.gbif.org/dataset/43411a7a-1503-4391-9791-e33801752053)).
- **Why a candidate, not the primary source:** Useful later as an optional region-level feature join (`occurrenceRemarks` statuses such as Present / Established / Introduced). It is a single-date map product, not a detection time series, and is out of scope for the primary occurrence table.

## Discarded alternatives

The options below were considered during early research and **not** selected as the primary vector source.

### Legacy VectorNet IPT `vndatabase` (Training Organization)

- **What:** Parallel DwC-A on `ipt.gbif.org` ([`r=vndatabase`](https://ipt.gbif.org/resource?r=vndatabase), UUID `e497586a-1bdf-4f69-90eb-645d615762c8`, ~277k rows) registered under a Training Organization publisher.
- **Why discarded:** Superseded by the official VectorNet observations dataset on GBIF.org. Larger row count but not the live VectorNet publisher registration used by the VectorNet Data Portal; citation metadata still references a flatfile/test-style resource path.

### GBIF SQL Data Cubes / full occurrence dumps

- **What:** GBIF occurrence warehouse queries and [data cubes](https://techdocs.gbif.org/en/data-use/data-cubes) over global occurrences (SQL-style extracts across many datasets).
- **Why discarded:** Asynchronous download jobs typically need **GBIF user credentials**; queues can take minutes; results mix many publishers and citizen-science observations without VectorNet’s surveillance protocols or consistent absence/effort metadata. Too heavy and too noisy for a Europe-focused vector–virus risk pipeline when VectorNet already publishes a curated DwC-A.

### VectorNet Data Portal and static map products

- **What:** The [VectorNet data portal](https://www.vectornetdata.org/) browse UI (aggregates VectorNet observations plus national/regional GBIF datasets); ECDC / VectorNet **static distribution map** portals and PNG/PDF map products.
- **Why discarded:** Useful for human inspection and discovery, but a poor reproducible training input (portal search UI, manual export, image or aggregated polygons, or multi-dataset GBIF occurrence downloads). Prefer the **official observations IPT DwC-A** (`r=vectornet_historical_data`, UUID `4abd984b-122c-44a0-8c92-b37e2f5299b1`) for checksummed refreshes of the primary occurrence table.

### VectorByte (`VecDyn` / `VecTraits`)

- **What:** Vector ecology data ecosystem ([VectorByte](https://www.vectorbyte.org/blog/welcome-to-the-vector-data-ecosystem))—`VecTraits` (trait / experimental data) and `VecDyn` (population / abundance time series).
- **Why discarded as primary source:** `VecTraits` is oriented to laboratory traits (e.g. thermal response), not Europe-wide surveillance occurrences. `VecDyn` coverage is fragmented relative to the unified ECDC/EFSA VectorNet database for EU/Mediterranean administrative geography. May remain useful later as **auxiliary features**, not as the main vector detection table.
