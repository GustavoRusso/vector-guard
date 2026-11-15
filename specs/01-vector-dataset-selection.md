# Vector dataset selection

The project uses **two** occurrence sources for vector detections that feed training:

1. **Primary:** [VectorNet observations](https://www.gbif.org/dataset/4abd984b-122c-44a0-8c92-b37e2f5299b1) (Europe / Mediterranean, CC BY 4.0).
2. **Secondary densifier:** [SPVECTORSURV](https://www.gbif.org/dataset/fc1dd9e3-ff53-4d57-9d8e-e29afbb955b8) (Spain surveillance, CC BY-NC 4.0).

Both are ingested as separate IPT DwC-A extracts, tagged with a closed `source` value, and **unioned** in notebook `08` into `data/02_interim/vectors_normalized.parquet`. SPVECTORSURV does **not** replace VectorNet and is **not** obtained by downloading the VectorNet Data Portal aggregation.

| Role | Dataset | License | Local raw path | Extract notebook |
|------|---------|---------|----------------|------------------|
| Primary | VectorNet observations | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | `data/01_raw/vector/` | [`01_extract_vectors.ipynb`](../notebooks/01_sources/01_extract_vectors.ipynb) |
| Secondary | SPVECTORSURV | [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) | `data/01_raw/vector_spvectorsurv/` | [`01b_extract_spvectorsurv.ipynb`](../notebooks/01_sources/01b_extract_spvectorsurv.ipynb) |

Interim / panel semantics (including `source` and the training filter): [`specs/04`](04-reference-data-and-panel-pipeline.md).

## Requirements that drove the choice

Vector Guard needs occurrence-like records that can be joined later to virus detections on space and time:

1. **Taxon / species** identifiable at least to genus or species within the medical and veterinary vector groups of interest.
2. **Geographic location** with reusable keys (coordinates and/or administrative codes) covering **Europe** (Mediterranean basin acceptable).
3. **Detection time** (`eventDate` or equivalent).
4. **Free access** with a **reproducible download** that does not require a logged-in user account when possible.
5. Preference for **surveillance / expert-validated** data over mixed citizen-science dumps.

## Selected primary source: VectorNet observations DwC-A

| Field | Value |
|-------|-------|
| Dataset | [VectorNet observations](https://www.gbif.org/dataset/4abd984b-122c-44a0-8c92-b37e2f5299b1) (ECDC / EFSA) |
| Resource key | `vectornet_historical_data` |
| GBIF dataset UUID | `4abd984b-122c-44a0-8c92-b37e2f5299b1` |
| DOI | [10.15468/f3k8r9](https://doi.org/10.15468/f3k8r9) |
| Latest download URL | `https://www.gbif.se/ipt/archive.do?r=vectornet_historical_data` |
| Format | Darwin Core Archive (DwC-A ZIP) |
| License | [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Local path | `data/01_raw/vector/` (not committed; re-fetched on demand) |
| Interim `source` value | `vectornet` |
| Extract notebook | [`notebooks/01_sources/01_extract_vectors.ipynb`](../notebooks/01_sources/01_extract_vectors.ipynb) |
| Loader | [`src/vector_guard/data.py`](../src/vector_guard/data.py) — `load_vector_detections()` |

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

### Why VectorNet observations was chosen as primary

- **Institutional fit:** Official ECDC / EFSA One Health vector surveillance under the VectorNet GBIF publisher, aligned with European public-health One Health vector surveillance use cases.
- **Schema fit:** Standardized DwC-A with coordinates, administrative geography IDs, and event dates—enough to support country-, NUTS-, or grid-level aggregation later.
- **Access model:** One HTTP GET of the latest ZIP from the GBIF Sweden IPT; **no GBIF account**, no async download queue, no API key.
- **Surveillance semantics:** Includes sampling protocol / effort fields, not only opportunistic presence points.
- **Publisher status:** Live registration on GBIF.org with DOI `10.15468/f3k8r9`, rather than a parallel Training Organization IPT resource.

### How to refresh

Run all cells in [`notebooks/01_sources/01_extract_vectors.ipynb`](../notebooks/01_sources/01_extract_vectors.ipynb). The notebook wipes `data/01_raw/vector/` (except `.gitkeep`), downloads the latest IPT archive, extracts it, and writes `manifest.json`.

```python
from vector_guard.data import load_vector_detections

df = load_vector_detections()
```

## Selected secondary source: SPVECTORSURV

| Field | Value |
|-------|-------|
| Dataset | [SPVECTORSURV](https://www.gbif.org/dataset/fc1dd9e3-ff53-4d57-9d8e-e29afbb955b8) — *Monitoring competent vectors of Crimea Congo Haemorragic Fever (ticks), West Nile and Rift Valley Fever in Spain (mosquitos)* (Ministerio de Agricultura, Pesca y Alimentación) |
| Resource key | `spvectorsurv` |
| GBIF dataset UUID | `fc1dd9e3-ff53-4d57-9d8e-e29afbb955b8` |
| DOI | [10.15470/fn1bet](https://doi.org/10.15470/fn1bet) |
| Latest download URL | `https://ipt.gbif.es/archive.do?r=spvectorsurv` |
| Format | Darwin Core Archive (DwC-A ZIP), published aligned with VectorNet column conventions |
| License | [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) |
| Local path | `data/01_raw/vector_spvectorsurv/` (not committed; re-fetched on demand; **separate** from VectorNet so `01` wipe cannot delete it) |
| Interim `source` value | `spvectorsurv` |
| Extract notebook | [`notebooks/01_sources/01b_extract_spvectorsurv.ipynb`](../notebooks/01_sources/01b_extract_spvectorsurv.ipynb) |
| Loader | [`src/vector_guard/data.py`](../src/vector_guard/data.py) — `load_spvectorsurv_detections()` / `load_all_vector_detections()` |

### What it provides

Expert One Health surveillance (EU4Health / EFSA-coordinated) densifying Spanish vector occurrences that are sparse or absent in VectorNet observations (notably western / southern mainland ticks relevant to Crimean–Congo haemorrhagic fever, plus mosquito sampling as published). Rows appear on the VectorNet Data Portal map because the portal **aggregates** national GBIF datasets; they are **not** inside the VectorNet observations IPT archive.

Coverage relevant to this project:

- **Geographic:** Spain (southern mainland via IREC; Balearic Islands via the University of the Balearic Islands; other Spanish sites as published).
- **Temporal:** project window January 2024–December 2026; published archive currently on the order of ~2.6k occurrences (exact span depends on the refresh).
- **Taxonomic groups:** ticks and mosquitoes as present in the published DwC-A (ingest the full occurrence table; do not tick-filter at extract).
- **Volume:** ~2.6k rows (v1.5-scale); small relative to VectorNet but large relative to Spain VectorNet tick coverage.

### Why secondary (not primary)

- Geography is Spain-only; Europe-wide modelling still depends on VectorNet.
- Series is still filling through 2026; refresh cadence is publisher-driven.
- License is **non-commercial** (CC BY-NC 4.0), stricter than VectorNet’s CC BY 4.0. Redistributing SPVECTORSURV rows commercially is not allowed; the combined interim / panel is **multi-license**.

### How to refresh

Run all cells in [`notebooks/01_sources/01b_extract_spvectorsurv.ipynb`](../notebooks/01_sources/01b_extract_spvectorsurv.ipynb). The notebook wipes only `data/01_raw/vector_spvectorsurv/` (except `.gitkeep`), downloads the latest Spanish IPT archive, extracts it, and writes `manifest.json`.

```python
from vector_guard.data import load_spvectorsurv_detections, load_all_vector_detections

sp = load_spvectorsurv_detections()
all_vectors = load_all_vector_detections()  # VectorNet + SPVECTORSURV with source
```

### Dedup vs VectorNet

No cross-source drop at clean time. Keep all rows from both extracts; QA may report soft overlaps on `(rounded lat/lon, scientific_name, year, month)`. Publisher `occurrenceID` namespaces differ and are not treated as a join key across sources.

## Candidates for future additions

Sources below are **not** part of the vector interim table yet. They may be joined later if geographic or pathogen coverage needs it.

### VectorDistributionStatus (admin-unit establishment snapshots)

- **What:** Expert establishment / presence–absence status by NUTS or GAUL unit, published as versioned DwC-A snapshots (e.g. [VectorDistributionStatus_2026](https://www.gbif.org/dataset/43411a7a-1503-4391-9791-e33801752053)).
- **Why a candidate, not a selected occurrence source:** Useful later as an optional region-level feature join (`occurrenceRemarks` statuses such as Present / Established / Introduced). It is a single-date map product, not a detection time series, and is out of scope for the occurrence table.

### Other VectorNet portal national datasets

- **What:** Additional Member State / project DwC-A datasets shown on [vectornetdata.org](https://www.vectornetdata.org/) alongside VectorNet observations and SPVECTORSURV.
- **Why deferred:** Each needs its own IPT URL, license review, and taxon-map refresh. Do not substitute a GBIF multi-dataset portal dump for selective IPT extracts.

## Discarded alternatives

The options below were considered during early research and **not** selected as the primary vector source (and are not used as the SPVECTORSURV ingest path).

### Legacy VectorNet IPT `vndatabase` (Training Organization)

- **What:** Parallel DwC-A on `ipt.gbif.org` ([`r=vndatabase`](https://ipt.gbif.org/resource?r=vndatabase), UUID `e497586a-1bdf-4f69-90eb-645d615762c8`, ~277k rows) registered under a Training Organization publisher.
- **Why discarded:** Superseded by the official VectorNet observations dataset on GBIF.org. Larger row count but not the live VectorNet publisher registration used by the VectorNet Data Portal; citation metadata still references a flatfile/test-style resource path.

### GBIF SQL Data Cubes / full occurrence dumps

- **What:** GBIF occurrence warehouse queries and [data cubes](https://techdocs.gbif.org/en/data-use/data-cubes) over global occurrences (SQL-style extracts across many datasets).
- **Why discarded:** Asynchronous download jobs typically need **GBIF user credentials**; queues can take minutes; results mix many publishers and citizen-science observations without VectorNet’s surveillance protocols or consistent absence/effort metadata. Too heavy and too noisy for a Europe-focused vector–virus risk pipeline when curated IPT DwC-As already exist.

### VectorNet Data Portal UI and multi-dataset GBIF downloads

- **What:** The [VectorNet data portal](https://www.vectornetdata.org/) browse UI (aggregates VectorNet observations plus national/regional GBIF datasets); ECDC / VectorNet **static distribution map** portals and PNG/PDF map products; one-shot GBIF downloads that OR many portal dataset keys.
- **Why discarded as ingest:** Useful for human inspection and discovery, but a poor reproducible training input (portal search UI, manual export, image or aggregated polygons, or account-gated multi-dataset jobs). Prefer **checksummed per-dataset IPT DwC-A** refreshes: VectorNet observations for the primary table, and the Spanish IPT for SPVECTORSURV as the selected secondary.

### VectorByte (`VecDyn` / `VecTraits`)

- **What:** Vector ecology data ecosystem ([VectorByte](https://www.vectorbyte.org/blog/welcome-to-the-vector-data-ecosystem))—`VecTraits` (trait / experimental data) and `VecDyn` (population / abundance time series).
- **Why discarded as primary source:** `VecTraits` is oriented to laboratory traits (e.g. thermal response), not Europe-wide surveillance occurrences. `VecDyn` coverage is fragmented relative to the unified ECDC/EFSA VectorNet database for EU/Mediterranean administrative geography. May remain useful later as **auxiliary features**, not as the main vector detection table.
