# Virus dataset selection

Decision record for the **virus detections** source used by Vector Guard (pathogen, geographic location, detection time), chosen to pair with the VectorNet vector dataset documented in [`specs/01-vector-dataset-selection.md`](01-vector-dataset-selection.md).

| Field | Value |
|-------|-------|
| Status | Selected and implemented (raw extract + loader) |
| Decision date | 2026-11 |
| Spec order | `02` (after vector dataset selection; before spatial-temporal matching) |

## Decision

Use the **ENA Portal REST API** as the primary virus detection source. The API exposes INSDC sequence metadata (ENA + NCBI GenBank + DDBJ) hosted by EMBL-EBI, filtered to the vector-borne virus taxa listed in [Target virus taxonomy](#target-virus-taxonomy).

| Field | Value |
|-------|-------|
| Dataset | [ENA Portal API](https://www.ebi.ac.uk/ena/portal/api/) (INSDC mirror) |
| Search endpoint | `https://www.ebi.ac.uk/ena/portal/api/search` |
| Result type | `result=sequence` |
| Format | TSV metadata extract (HTTP GET) |
| License / terms | [EMBL-EBI Terms of Use](https://www.ebi.ac.uk/about/terms-of-use/) (public open data; no account required) |
| Local path | `data/raw/virus/` (not committed; re-fetched on demand) |
| Extract notebook | [`notebooks/03_extract_viruses.ipynb`](../notebooks/03_extract_viruses.ipynb) |
| Loader | [`src/vector_guard/data.py`](../src/vector_guard/data.py) — `load_virus_detections()`, `VIRUS_VECTOR_TAXON_MAP` |
| EDA notebook | [`notebooks/04_eda_viruses.ipynb`](../notebooks/04_eda_viruses.ipynb) |

## Requirements that drove the choice

Virus records must be joinable later to VectorNet on space and time (join design is specified separately in `specs/03-spatial-temporal-matching-strategy.md`):

1. **Pathogen** identifiable by taxon (NCBI taxonomy ID and/or scientific name).
2. **Geographic location** covering at least **Europe**, optionally worldwide, with country and preferably region and/or coordinates.
3. **Detection / collection time** (`collection_date` or equivalent).
4. **Free access** with a **reproducible programmatic download** (prefer no logged-in user or manual browser export).
5. Alignment with VectorNet’s four vector groups (mosquito, tick, biting midge, sandfly), not a single US-only clinical network.
6. Preference for **lab-backed detections** (sequence / isolate metadata) over maps or paywalled outbreak digests alone.

## Candidate comparison

| Candidate | Geography | Access | Geo + time fields | Fit for Vector Guard |
|-----------|-----------|--------|-------------------|----------------------|
| **ENA / INSDC (selected)** | Europe + worldwide | Free HTTP API, no account | `country`, `location` / lat–lon, `collection_date`, `host`, `tax_id` | Best automation + Europe + worldwide sequence detections |
| NCBI Virus / Datasets | Europe + worldwide | Free; CLI or Datasets REST API | Country / region / date / host; fewer parsed lat–lon than ENA in one flat call | Strong alternative; overlaps INSDC; more tooling friction |
| Pathoplexus (LAPIS) | Europe + worldwide | Free LAPIS CSV/JSON API | Country / region / date / host for curated organisms | Excellent for listed arboviruses; incomplete vs full VectorNet pathogen set |
| ECDC Surveillance Atlas / seasonal reports | EU/EEA (NUTS / country) | Free; Atlas CSV often UI-driven | Aggregate case counts by admin unit and period | Official clinical aggregates; weak for automated point-level “detections” |
| VectorByte (`VecDyn` / `VecTraits`) | Global, uneven | Free / open ecosystem | Vector traits and dynamics; pathogen interaction data sparse as occurrence table | Better as auxiliary ecology features than virus detections |
| ArboNET (US CDC) | Primarily United States | Public maps / reports; not EU tabular dump | Human, animal, mosquito arbovirus surveillance | Gold-standard US surveillance; poor Europe overlap with VectorNet |

### ENA Portal REST API / INSDC (selected)

- **What:** EMBL-EBI’s European Nucleotide Archive Portal search API over the shared INSDC sequence warehouse (ENA, GenBank, DDBJ).
- **Strengths:** One flat `result=sequence` query returns pathogen taxon, country (often `Country: region, locality`), optional coordinates, collection date, host, and isolation source; no API key; Europe-dense submissions plus worldwide coverage; includes human, animal, and vector-derived isolates.
- **Weaknesses:** Sequence submission bias (not all clinical cases are sequenced); geo precision varies (country-only vs lat–lon); not a clinical case registry.
- **Why selected:** Meets free + programmatic + Europe (+ worldwide) requirements better than the other candidates while covering all target taxa in one API.

### NCBI Virus / GenBank (Datasets API)

- **What:** NCBI Virus / GenBank metadata via NCBI Datasets CLI or REST API (same underlying INSDC sequences as ENA for many records).
- **Strengths:** Authoritative virus portal; filter by taxon, geo, host, date; well documented metadata reports.
- **Why not primary:** Functionally overlaps ENA/INSDC. Datasets workflows often favor the CLI or multi-step package downloads; geographic fields are commonly country/region level with less emphasis on a single flat lat–lon TSV than ENA’s portal fields. Kept as a conceptual alternative / cross-check, not the extract path.

### Pathoplexus (LAPIS)

- **What:** Open pathogen sequence sharing platform with per-organism LAPIS APIs (e.g. West Nile, dengue, chikungunya, Zika, CCHF, yellow fever).
- **Strengths:** Curated arbovirus focus; simple CSV metadata endpoints; Europe + worldwide; modern API.
- **Why not primary:** Organism coverage is curated and incomplete relative to VectorNet’s full vector-group pathogen set (e.g. Usutu, Sindbis, Schmallenberg, Toscana / sandfly fever Naples, bluetongue). Useful later as a secondary curated feed, not the single source of truth.

### ECDC Surveillance Atlas and seasonal reports

- **What:** EU/EEA routine surveillance aggregates (e.g. West Nile, dengue, TBE, chikungunya) via the [Surveillance Atlas](https://atlas.ecdc.europa.eu/public/) and seasonal dashboards (CSV exports for some diseases).
- **Strengths:** Official clinical case counts at NUTS/country scale; strong Europe institutional alignment with VectorNet.
- **Why not primary:** Often UI-driven export rather than a stable zero-auth bulk API; records are **aggregated cases**, not individual lab detections with host/isolate metadata; worldwide coverage is out of scope. May inform validation or labels later, not the raw virus detection table.

### VectorByte (`VecDyn` / `VecTraits`)

- **What:** Vector ecology ecosystem focused on traits, competence, and population dynamics for vector-borne disease research.
- **Strengths:** Strong vector–pathogen ecology context.
- **Why not primary:** Not a systematic virus detection occurrence feed with pathogen + place + time for Europe-wide modelling. Same conclusion as in the vector dataset spec: auxiliary features only.

### ArboNET (US CDC)

- **What:** US national arbovirus surveillance (humans, blood donors, sentinel animals, mosquito isolations).
- **Strengths:** Structured public-health arbovirus surveillance gold standard in the US.
- **Why not primary:** Geography is primarily the United States; does not cover European VectorNet space. Discarded for Europe-first matching.

## Selection rationale (summary)

1. **Access:** Free, no account, single HTTP search API.
2. **Coverage:** Europe-strong + worldwide sequence detections.
3. **Schema:** Pathogen + place + time (+ host) in one table shape suitable for a `data/raw/virus/` extract.
4. **Taxon breadth:** One query pattern covers all viruses tied to VectorNet’s four vector groups (see below).
5. **Alternatives fail a hard requirement:** ArboNET (not Europe), ECDC Atlas (aggregates / manual export), Pathoplexus (incomplete pathogen set), VectorByte (not virus detections), NCBI Datasets (redundant INSDC with more extract friction).

## Target virus taxonomy

Each target taxon is mapped to a VectorNet vector group so features can relate mosquito / tick / midge / sandfly presence to the matching pathogens. NCBI Taxonomy IDs below are the **ENA-verified** `tax_tree(...)` IDs used in `VIRUS_VECTOR_TAXON_MAP` and the extract notebook (some early candidate IDs returned empty trees in ENA and were replaced).

| Pathogen (canonical name) | NCBI tax ID(s) used in extract | VectorNet vector group | Primary vector genera (indicative) |
|---------------------------|--------------------------------|------------------------|------------------------------------|
| West Nile virus | `11082` | Mosquito (`Culicidae`) | `Culex`, `Aedes` |
| Usutu virus | `64286` | Mosquito (`Culicidae`) | `Culex`, `Aedes` |
| Dengue virus | `12637` | Mosquito (`Culicidae`) | `Aedes` |
| Chikungunya virus | `37124` | Mosquito (`Culicidae`) | `Aedes` |
| Zika virus | `64320` | Mosquito (`Culicidae`) | `Aedes` |
| Sindbis virus | `11034` | Mosquito (`Culicidae`) | `Culex`, `Aedes` |
| Rift Valley fever virus | `11588` | Mosquito (`Culicidae`) | `Aedes`, `Culex` |
| Tick-borne encephalitis virus | `11084` | Tick (`Ixodida`) | `Ixodes`, `Dermacentor`, `Haemaphysalis` |
| Crimean-Congo hemorrhagic fever virus | `3052518` (`Orthonairovirus haemorrhagiae`) | Tick (`Ixodida`) | `Hyalomma` |
| Bluetongue virus | `40051` | Biting midge (`Ceratopogonidae`) | `Culicoides` |
| Schmallenberg virus | `1133363` | Biting midge (`Ceratopogonidae`) | `Culicoides` |
| Sandfly fever Naples phlebovirus / Toscana virus | `11590`, `206160`, `1933189` | Sandfly (`Phlebotominae`) | `Phlebotomus` |

### Implemented ENA extract

[`notebooks/03_extract_viruses.ipynb`](../notebooks/03_extract_viruses.ipynb) implements:

- `result=sequence` with `tax_tree(<tax_id>)` for each tax ID above (`limit=0`)
- Keep rows with non-empty `country` or `collection_date`; dedupe by `accession`
- Tag rows with `pathogen_name` and `vector_group`
- Write `data/raw/virus/virus_detections.tsv` and `manifest.json` (fetch time, per-pathogen counts, SHA-256, citation)

Load in other notebooks:

```python
from vector_guard.data import load_virus_detections

df = load_virus_detections()
```

### Auxiliary signal from VectorNet

VectorNet’s `dynamicProperties` column sometimes embeds pathogen strings (e.g. `{"pathogen": "West Nile virus"}`). Those sparse rows are **not** the virus dataset; they may be used later as an optional validation / enrichment signal during EDA or matching.

## Out of scope for this decision

- Spatial-temporal join implementation (design in [`specs/03-spatial-temporal-matching-strategy.md`](03-spatial-temporal-matching-strategy.md))
- Cleaning / ISO-2 / H3 feature engineering beyond the raw extract
- Clinical diagnosis or exact introduction-date prediction

## Related project files

| Path | Role |
|------|------|
| [`specs/01-vector-dataset-selection.md`](01-vector-dataset-selection.md) | Paired vector source (VectorNet) |
| [`specs/03-spatial-temporal-matching-strategy.md`](03-spatial-temporal-matching-strategy.md) | Join design (H3 + country) |
| [`README.md`](../README.md) | Published virus data table and refresh steps |
| [`notebooks/03_extract_viruses.ipynb`](../notebooks/03_extract_viruses.ipynb) | ENA extract |
| [`notebooks/04_eda_viruses.ipynb`](../notebooks/04_eda_viruses.ipynb) | Initial virus EDA |
| [`src/vector_guard/data.py`](../src/vector_guard/data.py) | `VIRUS_VECTOR_TAXON_MAP`, `load_virus_detections()` |
