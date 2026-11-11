# Virus dataset selection

Decision record for the **virus detections** sources used by Vector Guard (pathogen, geographic location, detection time), chosen to pair with the VectorNet vector dataset documented in [`specs/01-vector-dataset-selection.md`](01-vector-dataset-selection.md).

| Field | Value |
|-------|-------|
| Status | **Multi-source strategy decided** — v1 ENA `result=sequence` extract is implemented; multi-source upgrade + expanded taxonomy are **Planned** (document this path; do not implement in this pass) |
| Decision date | 2026-11 (initial ENA selection); 2026-11 (multi-source expansion) |
| Spec order | `02` (after vector dataset selection; before spatial-temporal matching) |

## Decision

Use a **multi-source programmatic virus detection strategy** written into a single unified table under `data/raw/virus/`. The feeds combine INSDC sequence metadata (via ENA Portal + curated portals) with European / Mediterranean outbreak and surveillance tables so that pathogen + place + time coverage is dense enough for VectorNet joins.

| Field | Value |
|-------|-------|
| Primary sequence warehouse | [ENA Portal API](https://www.ebi.ac.uk/ena/portal/api/) (INSDC: ENA + GenBank + DDBJ) |
| ENA search endpoint | `https://www.ebi.ac.uk/ena/portal/api/search` |
| ENA result types (target) | `result=sequence`, `result=read_run`, and `result=sample` (coordinate / date backfill) |
| Curated sequence enrichment | [BV-BRC Genome REST API](https://www.bv-brc.org/api/genome/); [Pathoplexus LAPIS](https://pathoplexus.org/) |
| Outbreak / admin surveillance | FAO EMPRES-i (point outbreaks); ECDC Surveillance Atlas / seasonal tables (NUTS3 / GAUL) |
| Format | Unified TSV metadata extract (`virus_detections.tsv`) |
| Local path | `data/raw/virus/` (not committed; re-fetched on demand) |
| Extract notebook | [`notebooks/03_extract_viruses.ipynb`](../notebooks/03_extract_viruses.ipynb) (upgrade Planned) |
| Loader | [`src/vector_guard/data.py`](../src/vector_guard/data.py) — `load_virus_detections()`, `VIRUS_VECTOR_TAXON_MAP` (taxonomy expansion Planned) |
| EDA notebook | [`notebooks/04_eda_viruses.ipynb`](../notebooks/04_eda_viruses.ipynb) |

**Why multi-source (not replace ENA):** ENA `result=sequence` alone yields many rows but sparse exact coordinates (≈2.6% overall; ≈0.8% in Europe/Med in the current extract EDA) and drops sequences that lack both `country` and `collection_date` on the sequence flatfile. Read runs, BioSamples, curated INSDC portals, and outbreak feeds densify **geolocation** and add non-sequenced Europe detections without abandoning a free, reproducible download path.

## Requirements that drove the choice

Virus records must be joinable later to VectorNet on space and time (join design is specified in [`specs/03-spatial-temporal-matching-strategy.md`](03-spatial-temporal-matching-strategy.md)):

1. **Pathogen** identifiable by taxon (NCBI taxonomy ID and/or scientific name).
2. **Geographic location** covering at least **Europe**, optionally worldwide, with country and preferably region and/or coordinates.
3. **Detection / collection time** (`collection_date` or equivalent).
4. **Free access** with a **reproducible programmatic download** (prefer no logged-in user or manual browser export).
5. Alignment with VectorNet’s four vector groups (mosquito, tick, biting midge, sandfly), not a single US-only clinical network.
6. Preference for **lab-backed detections** (sequence / isolate metadata), with official outbreak / admin surveillance allowed as a complementary geolocalized feed when sequences are sparse.
7. Enough **Tier 1 (H3)** candidates after cleaning that Europe/Med modelling is not forced almost entirely to country Tier 2 (see coordinate and subnational rules in specs `03` / `04`).

## Candidate comparison

| Candidate | Geography | Access | Geo + time fields | Role in Vector Guard |
|-----------|-----------|--------|-------------------|----------------------|
| **ENA / INSDC `sequence` + `read_run` + `sample`** | Europe + worldwide | Free HTTP API, no account | `country`, `location` / lat–lon, BioSample checklist coords, `collection_date`, `host`, `tax_id` | **Core INSDC warehouse** (assembled seq + runs + sample backfill) |
| **BV-BRC Genome API** | Europe + worldwide | Free REST API | Curated / text-mined lat–lon, geographic location, collection year | **INSDC enrichment** for missing coords / place strings |
| **Pathoplexus (LAPIS)** | Europe + worldwide | Free LAPIS CSV/JSON API | Country, division (admin1), location, date, host for listed arboviruses | **Curated arbovirus feed**; merge by INSDC accession where present |
| **FAO EMPRES-i** | Global (strong Europe/Med vet coverage) | Programmatic / open outbreak extracts where available | Point lat–lon + observation / reporting dates for zoonotic & veterinary arboviruses | **Outbreak point detections** (non-sequence Tier 1 densifier) |
| **ECDC Surveillance Atlas / seasonal reports** | EU/EEA (NUTS / country) | Free; prefer stable programmatic or documented CSV where available | Aggregate cases by NUTS3/GAUL and period | **Admin-unit Europe labels** aligned with VectorNet `higherGeographyID` |
| NCBI Virus / Datasets | Europe + worldwide | Free; CLI or Datasets REST API | Country / region / date / host | Overlaps INSDC; **not** a required extract path (ENA + BV-BRC cover the need) |
| VectorByte (`VecDyn` / `VecTraits`) | Global, uneven | Free / open ecosystem | Vector traits and dynamics | Auxiliary ecology features only |
| ArboNET (US CDC) | Primarily United States | Public maps / reports | Human, animal, mosquito arbovirus surveillance | Discarded for Europe-first VectorNet pairing |

### Feed definitions (locked for the upgrade)

#### 1. ENA Portal — `result=sequence` (assembled INSDC)

- **What:** EMBL-EBI European Nucleotide Archive Portal search over assembled sequence records (ENA + GenBank + DDBJ).
- **Role:** Baseline pathogen + country + date table for all taxa in [Target virus taxonomy](#target-virus-taxonomy).
- **License / terms:** [EMBL-EBI Terms of Use](https://www.ebi.ac.uk/about/terms-of-use/) (public open data; no account required).
- **v1 status:** Implemented in [`notebooks/03_extract_viruses.ipynb`](../notebooks/03_extract_viruses.ipynb) (`tax_tree(<tax_id>)`, keep non-empty `country` or `collection_date`, dedupe by `accession`).

#### 2. ENA Portal — `result=read_run` + `result=sample`

- **What:** Raw sequencing runs (SRA/ENA) and BioSample metadata for the same `tax_tree(...)` targets.
- **Role:** Capture modern genomic-surveillance submissions that never land as assembled `sequence` records; use BioSample checklist fields to supply `lat`/`lon` and `collection_date`, and **backfill** missing coordinates onto sequence rows via `sample_accession`.
- **Why required:** Sequence flatfiles often omit place/time that exist on the linked sample; runs add extra detections without leaving INSDC.
- **Implementation status:** Planned in the extract notebook upgrade (same endpoint family as today).

#### 3. BV-BRC Genome REST API

- **What:** [BV-BRC](https://www.bv-brc.org/) curated viral genome metadata (`https://www.bv-brc.org/api/genome/`), largely over INSDC accessions.
- **Role:** Enrichment of lat/lon and place strings via curated / text-mined fields (`latitude`, `longitude`, `geographic_location`, `collection_year`) that are blank on raw ENA `location`.
- **Merge key:** Normalized INSDC accession (and sample accession when present).
- **Implementation status:** Planned secondary feed in the extract notebook upgrade.

#### 4. Pathoplexus (LAPIS)

- **What:** Open pathogen sequence sharing platform with per-organism LAPIS CSV/JSON APIs (e.g. West Nile, dengue, chikungunya, Zika, CCHF, yellow fever).
- **Role:** Curated arbovirus metadata with standardized `country`, `division` (first-level admin region), and `location`; merge by INSDC accession when available.
- **Why not sole source:** Organism list is curated and incomplete vs the full VectorNet-linked pathogen set (e.g. Usutu, Sindbis, Schmallenberg, Toscana / Naples, bluetongue, EHDV).
- **Implementation status:** Planned secondary feed for listed organisms.

#### 5. FAO EMPRES-i and ECDC NUTS3 / seasonal surveillance

- **What:**
  - **FAO EMPRES-i** (Global Animal Disease Information System) / related WOAH outbreak feeds: point-level veterinary and zoonotic outbreak events with latitude, longitude, and observation/reporting dates (e.g. West Nile, bluetongue, Rift Valley fever, CCHF, Schmallenberg, Usutu, EHDV).
  - **ECDC Surveillance Atlas** and seasonal arbovirus tables: EU/EEA human (and related) surveillance aggregates at **NUTS3 / GAUL** codes and periods—aligned with VectorNet `higherGeographyID`.
- **Role:** Geolocalized **non-sequence** detections that densify Europe/Med Tier 1 (exact GPS) and Tier 1 via NUTS3 centroids (see [`specs/03-spatial-temporal-matching-strategy.md`](03-spatial-temporal-matching-strategy.md)).
- **Caveat:** Clinical/outbreak aggregates ≠ sequenced isolates; keep `source` distinct and treat as complementary labels, not a replacement for sequence bias documentation.
- **Implementation status:** Planned secondary feeds; prefer reproducible programmatic or checksummed CSV downloads over one-off UI clicks.

### Discarded or non-required as extract paths

#### NCBI Virus / GenBank (Datasets API)

- **Why not a required feed:** Same underlying INSDC sequences as ENA for many records; more CLI / multi-step friction than ENA Portal + BV-BRC enrichment. May remain a conceptual cross-check only.

#### VectorByte (`VecDyn` / `VecTraits`)

- **Why not a virus detection feed:** Trait and population dynamics ecosystem, not a systematic pathogen + place + time occurrence table. Auxiliary ecology features only (same conclusion as in the vector dataset spec).

#### ArboNET (US CDC)

- **Why discarded:** Geography is primarily the United States; poor overlap with European VectorNet space.

## Selection rationale (summary)

1. **Access:** Prefer free, account-free, reproducible HTTP/API or checksummed bulk extracts.
2. **Coverage:** Europe-strong + worldwide sequences, plus Europe/Med outbreak and NUTS3 densification.
3. **Schema:** One unified `data/raw/virus/virus_detections.tsv` shape with an explicit `source` column.
4. **Taxon breadth:** One `VIRUS_VECTOR_TAXON_MAP` drives sequence/run queries and pathogen tagging across feeds.
5. **Geo density:** Multi-source + sample backfill + curated coords address the sparse ENA `location` field without inventing street-level precision at extract time (centroid promotion is specified in specs `03` / `04`).
6. **Do not replace ENA wholesale:** Secondary portals overlap INSDC; outbreak feeds complement rather than substitute sequence detections.

## Unified raw schema and deduplication

Target output of the upgraded extract: `data/raw/virus/virus_detections.tsv` plus `manifest.json` (fetch time, per-source and per-pathogen counts, SHA-256, citations).

### Canonical columns

| Column | Meaning |
|--------|---------|
| `record_id` | Stable unique id within the unified extract (e.g. `{source}:{native_id}`) |
| `source` | One of `ena_sequence`, `ena_read_run`, `bvbrc`, `pathoplexus`, `empres_i`, `ecdc_atlas` |
| `accession` | INSDC sequence / genome accession when applicable; empty for pure outbreak rows |
| `sample_accession` | BioSample / sample accession when known |
| `study_accession` | Study / project accession when known |
| `pathogen_name` | Canonical name from [Target virus taxonomy](#target-virus-taxonomy) |
| `vector_group` | `mosquito` \| `tick` \| `biting_midge` \| `sandfly` |
| `query_tax_id` | Tax ID used in the query (when applicable) |
| `scientific_name` | Source scientific / organism name |
| `tax_id` | NCBI tax ID when available |
| `country` | Country token or ENA-style `Country: region, locality` string |
| `subnational_region` | Parsed admin1/admin2 / division / locality string when available |
| `nuts_id` | NUTS or GAUL-style code when available (ECDC / aligned feeds) |
| `lat` | Decimal latitude when known at extract time |
| `lon` | Decimal longitude when known at extract time |
| `coord_source` | `exact_gps` \| `sample_backfill` \| `none` (centroid promotion happens in cleaning, not here) |
| `collection_date` | Collection / observation / reporting date string as published |
| `host` | Host organism when available |
| `isolation_source` | Isolation / specimen source when available |

### Deduplication rules (Planned)

**INSDC-backed sources** (`ena_sequence`, `ena_read_run`, `bvbrc`, `pathoplexus`):

1. Normalize accession strings (trim; consistent case) and group by `accession` when present.
2. Else group by `sample_accession` when present (especially for runs / samples without a sequence accession).
3. Within a group, **merge to the richest non-null metadata**: prefer non-null `lat`/`lon`, then `subnational_region`, then `collection_date`, then `host` / `isolation_source`. Prefer `coord_source=exact_gps` over `sample_backfill` over `none`.
4. Retain a deterministic primary `source` for the merged row (prefer `ena_sequence` when a sequence accession exists; else `ena_read_run`; else `bvbrc` / `pathoplexus` in that order unless another source alone provides coordinates).

**Outbreak / surveillance sources** (`empres_i`, `ecdc_atlas`):

1. Do **not** collapse into INSDC accession groups.
2. Key by native outbreak / event id when published; else by `(source, pathogen_name, nuts_id | lat/lon rounded consistently, collection_date)`.
3. Keep them as separate detection rows so sequence bias and clinical/outbreak reporting remain distinguishable via `source`.

**Keep filter (all sources):** retain rows with usable place and/or time after source-specific parsing (at minimum non-empty `country` / `nuts_id` / `(lat,lon)` **or** `collection_date`), then apply the merge rules above.

## Target virus taxonomy

Each target taxon is mapped to a VectorNet vector group so features can relate mosquito / tick / midge / sandfly presence to the matching pathogens. NCBI Taxonomy IDs are intended for ENA `tax_tree(...)` (and analogous BV-BRC / Pathoplexus filters). Some IDs may need re-verification against live ENA trees at implementation time (empty trees → replace with a verified sibling / species ID, as done for CCHFV / Toscana in v1).

### Currently implemented (v1 extract)

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

### Planned additions to `VIRUS_VECTOR_TAXON_MAP`

Add Europe / Mediterranean–relevant pathogens (and broaden sandfly coverage) when upgrading the extract and `VIRUS_VECTOR_TAXON_MAP` in [`src/vector_guard/data.py`](../src/vector_guard/data.py):

| Pathogen (canonical name) | NCBI tax ID(s) (indicative) | VectorNet vector group | Notes |
|---------------------------|-----------------------------|------------------------|-------|
| Batai orthobunyavirus | `11574` | Mosquito (`Culicidae`) | Europe mosquito orthobunyavirus |
| Tahyna / California encephalitis orthobunyavirus | `11577` | Mosquito (`Culicidae`) | Confirm ENA tree coverage for Tahyna vs parent |
| Inkoo orthobunyavirus | `11576` | Mosquito (`Culicidae`) | Northern Europe |
| Japanese encephalitis virus | `11072` | Mosquito (`Culicidae`) | Travel / imported + worldwide context |
| Yellow fever virus | `11089` | Mosquito (`Culicidae`) | Pathoplexus overlap; travel / imported context |
| Louping ill virus | `11086` | Tick (`Ixodida`) | UK / Europe tick flavivirus |
| Omsk hemorrhagic fever virus | `11083` | Tick (`Ixodida`) | Tick flavivirus |
| Thogoto / Bourbon thogotovirus | `11320`, `3052728` | Tick (`Ixodida`) | Verify live tax IDs at extract time |
| Jingmen tick virus | `1559366` | Tick (`Ixodida`) | Emerging tick-associated virus |
| Alongshan virus | `2026119` | Tick (`Ixodida`) | Emerging tick-associated virus |
| Epizootic hemorrhagic disease virus (EHDV) | `40050` | Biting midge (`Ceratopogonidae`) | Recent Europe outbreaks; EMPRES-i relevance |
| African horse sickness virus | `40052` | Biting midge (`Ceratopogonidae`) | Mediterranean / Africa veterinary |
| Akabane orthobunyavirus | `11572` | Biting midge (`Ceratopogonidae`) | Culicoides-borne Simbu group |
| Phlebovirus (Mediterranean sandfly fever complex) | `11584` (+ species as needed) | Sandfly (`Phlebotominae`) | Broaden beyond Naples/Toscana; include Sandfly fever Sicilian, Massilia, Granada, Punique as verified |

Keep tagging outbreak rows (`empres_i`, `ecdc_atlas`) with the same `pathogen_name` / `vector_group` vocabulary even when no NCBI tax ID is present on the source row.

### Current ENA extract (v1 — still live)

[`notebooks/03_extract_viruses.ipynb`](../notebooks/03_extract_viruses.ipynb) currently implements:

- `result=sequence` with `tax_tree(<tax_id>)` for each **v1** tax ID above (`limit=0`)
- Keep rows with non-empty `country` or `collection_date`; dedupe by `accession`
- Tag rows with `pathogen_name` and `vector_group`
- Write `data/raw/virus/virus_detections.tsv` and `manifest.json` (fetch time, per-pathogen counts, SHA-256, citation)

Load in other notebooks:

```python
from vector_guard.data import load_virus_detections

df = load_virus_detections()
```

### Planned extract upgrade (do not implement in the docs-only pass)

When implementing later, [`notebooks/03_extract_viruses.ipynb`](../notebooks/03_extract_viruses.ipynb) should:

1. Expand `VIRUS_VECTOR_TAXON_MAP` to the planned taxa (verify ENA `tax_tree` counts first).
2. Fetch ENA `sequence`, `read_run`, and linked `sample` metadata; apply sample coordinate / date backfill.
3. Fetch BV-BRC and Pathoplexus for overlapping taxa; fetch EMPRES-i and ECDC NUTS3 / seasonal tables for listed pathogens.
4. Normalize into the [unified raw schema](#unified-raw-schema-and-deduplication), apply dedupe rules, write `virus_detections.tsv` + `manifest.json` with **per-source** and per-pathogen counts.

Cleaning, ISO-2, subnational centroid → H3, and panel merge remain owned by specs [`03`](03-spatial-temporal-matching-strategy.md) and [`04`](04-reference-data-and-panel-pipeline.md) (`09_clean_viruses`, `10_merge_modelling_panel`).

### Auxiliary signal from VectorNet

VectorNet’s `dynamicProperties` column sometimes embeds pathogen strings (e.g. `{"pathogen": "West Nile virus"}`). Those sparse rows are **not** part of the multi-source virus extract; they may be used later as an optional validation / enrichment signal during EDA or matching.

## Out of scope for this decision

- Spatial-temporal join implementation and subnational centroid promotion (design in [`specs/03-spatial-temporal-matching-strategy.md`](03-spatial-temporal-matching-strategy.md) and [`specs/04-reference-data-and-panel-pipeline.md`](04-reference-data-and-panel-pipeline.md))
- Implementing the multi-source extract notebook, loader schema changes, or taxonomy code updates in this documentation pass
- Clinical diagnosis or exact introduction-date prediction

## Related project files

| Path | Role |
|------|------|
| [`specs/01-vector-dataset-selection.md`](01-vector-dataset-selection.md) | Paired vector source (VectorNet) |
| [`specs/03-spatial-temporal-matching-strategy.md`](03-spatial-temporal-matching-strategy.md) | Join design (H3 + country; subnational Tier 1 path) |
| [`specs/04-reference-data-and-panel-pipeline.md`](04-reference-data-and-panel-pipeline.md) | Reference tables, virus clean/resolve, modelling panel |
| [`README.md`](../README.md) | Published virus data table and refresh steps |
| [`ROADMAP.md`](../ROADMAP.md) | Build status for multi-source extract / taxonomy expansion |
| [`notebooks/03_extract_viruses.ipynb`](../notebooks/03_extract_viruses.ipynb) | Virus extract (v1 ENA sequence; upgrade Planned) |
| [`notebooks/04_eda_viruses.ipynb`](../notebooks/04_eda_viruses.ipynb) | Initial virus EDA |
| [`src/vector_guard/data.py`](../src/vector_guard/data.py) | `VIRUS_VECTOR_TAXON_MAP`, `load_virus_detections()` |
