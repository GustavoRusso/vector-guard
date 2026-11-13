# Virus dataset selection

Decision record for the **virus detections** sources used by Vector Guard (pathogen, geographic location, detection time), chosen to pair with the VectorNet vector dataset documented in [`specs/01-vector-dataset-selection.md`](01-vector-dataset-selection.md).

| Field | Value |
|-------|-------|
| Status | **Implemented** — multi-source extract (6 feeds), 26-pathogen taxonomy, unified 19-column TSV |
| Decision date | 2026-11 (initial ENA selection); 2026-11 (multi-source expansion implemented) |
| Spec order | `02` (after vector dataset selection; before spatial-temporal matching) |

## Decision

Use a **multi-source programmatic virus detection strategy** written into a single unified table under `data/01_raw/virus/`. The feeds combine INSDC sequence metadata (via ENA Portal + curated portals) with European / Mediterranean outbreak and surveillance tables so that pathogen + place + time coverage is dense enough for VectorNet joins.

| Field | Value |
|-------|-------|
| Primary sequence warehouse | [ENA Portal API](https://www.ebi.ac.uk/ena/portal/api/) (INSDC: ENA + GenBank + DDBJ) |
| ENA search endpoint | `https://www.ebi.ac.uk/ena/portal/api/search` |
| ENA result types | `result=sequence`, `result=read_run`, and `result=sample` (coordinate / date backfill) |
| Curated sequence enrichment | [BV-BRC Genome REST API](https://www.bv-brc.org/api/genome/); [Pathoplexus LAPIS](https://pathoplexus.org/) |
| Outbreak / admin surveillance | FAO EMPRES-i BigQuery CSV; ECDC WNV weekly/monthly NUTS3 reports |
| Format | Unified TSV metadata extract (`virus_detections.tsv`) |
| Local path | `data/01_raw/virus/` (not committed; re-fetched on demand) |
| Extract notebook | [`notebooks/01_sources/03_extract_viruses.ipynb`](../notebooks/01_sources/03_extract_viruses.ipynb) |
| Loader / helpers | [`src/vector_guard/data.py`](../src/vector_guard/data.py) — `load_virus_detections()`, `VIRUS_VECTOR_TAXON_MAP`; [`src/vector_guard/virus_extract.py`](../src/vector_guard/virus_extract.py) — `VIRUS_RAW_COLUMNS`, normalize / dedupe |
| Inspect notebook | [`notebooks/01_sources/04_inspect_viruses.ipynb`](../notebooks/01_sources/04_inspect_viruses.ipynb) |

**Why multi-source (not replace ENA):** ENA `result=sequence` alone yields many rows but sparse exact coordinates and drops sequences that lack both `country` and `collection_date` on the sequence flatfile. Read runs, BioSamples, curated INSDC portals, and outbreak feeds densify **geolocation** and add non-sequenced Europe detections without abandoning a free, reproducible download path.

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
| **FAO EMPRES-i** | Global (strong Europe/Med vet coverage) | Programmatic BigQuery CSV API | Point lat–lon + observation / reporting dates for zoonotic & veterinary arboviruses | **Outbreak point detections** (non-sequence Tier 1 densifier) |
| **ECDC seasonal WNV NUTS3 reports** | EU/EEA (NUTS / GAUL) | Free HTML-embedded base64 CSV downloads | Aggregate cases by NUTS3/GAUL and period | **Admin-unit Europe labels** aligned with VectorNet `higherGeographyID` |
| NCBI Virus / Datasets | Europe + worldwide | Free; CLI or Datasets REST API | Country / region / date / host | Overlaps INSDC; **not** a required extract path (ENA + BV-BRC cover the need) |
| VectorByte (`VecDyn` / `VecTraits`) | Global, uneven | Free / open ecosystem | Vector traits and dynamics | Auxiliary ecology features only |
| ArboNET (US CDC) | Primarily United States | Public maps / reports | Human, animal, mosquito arbovirus surveillance | Discarded for Europe-first VectorNet pairing |

### Feed definitions (implemented)

#### 1. ENA Portal — `result=sequence` (assembled INSDC)

- **What:** EMBL-EBI European Nucleotide Archive Portal search over assembled sequence records (ENA + GenBank + DDBJ).
- **Endpoint:** `https://www.ebi.ac.uk/ena/portal/api/search` (`result=sequence`, `tax_tree(<tax_id>)`).
- **Role:** Baseline pathogen + country + date table for all taxa in [Target virus taxonomy](#target-virus-taxonomy).
- **License / terms:** [EMBL-EBI Terms of Use](https://www.ebi.ac.uk/about/terms-of-use/) (public open data; no account required).
- **Status:** Implemented (`source=ena_sequence`).

#### 2. ENA Portal — `result=read_run` + `result=sample`

- **What:** Raw sequencing runs (SRA/ENA) and BioSample metadata for the same `tax_tree(...)` targets.
- **Endpoint:** same Portal search URL (`result=read_run`; batched `POST` `includeAccessions` for `result=sample`).
- **Role:** Capture modern genomic-surveillance submissions that never land as assembled `sequence` records; use BioSample checklist fields to supply `lat`/`lon` and `collection_date`, and **backfill** missing coordinates onto sequence / run rows via `sample_accession` (`coord_source=sample_backfill`).
- **Status:** Implemented (`source=ena_read_run` + sample backfill onto both ENA sources).

#### 3. BV-BRC Genome REST API

- **What:** [BV-BRC](https://www.bv-brc.org/) curated viral genome metadata.
- **Endpoint:** `https://www.bv-brc.org/api/genome/` (`Accept: text/tsv`, `in(taxon_lineage_ids,(...))`, `limit(25000, offset)`).
- **Role:** Enrichment of lat/lon and place strings via curated / text-mined fields; merge by normalized INSDC accession (and sample accession when present).
- **Status:** Implemented (`source=bvbrc`).

#### 4. Pathoplexus (LAPIS)

- **What:** Open pathogen sequence sharing platform with per-organism LAPIS TSV APIs.
- **Endpoint:** `https://lapis.pathoplexus.org/{slug}/sample/details?dataFormat=tsv` for `west-nile`, `dengue`, `chikungunya`, `zika`, `cchf`, `yellow-fever`.
- **Role:** Curated arbovirus metadata with standardized country / admin1 / location / date; merge by INSDC accession when available.
- **Status:** Implemented (`source=pathoplexus`) for the listed organisms.

#### 5. FAO EMPRES-i+ BigQuery CSV

- **What:** Point-level veterinary and zoonotic outbreak events.
- **Endpoint:** `https://api.data.apps.fao.org/api/v2/bigquery` with FAO `animal-major-disease-parameterized-query.sql` (no authentication).
- **Diseases queried:** West Nile Fever, Bluetongue, Rift Valley fever, Schmallenberg, African horse sickness, Japanese Encephalitis (`2000-01-01` → current date); exclude `diagnosis_status == "Denied"`.
- **Role:** Geolocalized **non-sequence** detections that densify Tier 1 GPS.
- **Status:** Implemented (`source=empres_i`).

#### 6. ECDC seasonal WNV NUTS3 reports

- **What:** EU/EEA West Nile virus seasonal surveillance at NUTS3 / GAUL with onset dates and human / equid / bird case flags.
- **Endpoints:** `https://wnv-weekly.ecdc.europa.eu/` and `https://wnv-monthly.ecdc.europa.eu/` (embedded `data:text/csv;base64,...` tables). Note: `atlas.ecdc.europa.eu` has no public API and is **not** used.
- **Role:** Admin-unit Europe labels aligned with VectorNet `higherGeographyID` (`nuts_id`).
- **Status:** Implemented (`source=ecdc_atlas`; West Nile virus only for this feed).

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
3. **Schema:** One unified `data/01_raw/virus/virus_detections.tsv` shape with an explicit `source` column.
4. **Taxon breadth:** One `VIRUS_VECTOR_TAXON_MAP` drives sequence/run queries and pathogen tagging across feeds.
5. **Geo density:** Multi-source + sample backfill + curated coords address the sparse ENA `location` field without inventing street-level precision at extract time (centroid promotion is specified in specs `03` / `04`).
6. **Do not replace ENA wholesale:** Secondary portals overlap INSDC; outbreak feeds complement rather than substitute sequence detections.

## Unified raw schema and deduplication

Output of the extract: `data/01_raw/virus/virus_detections.tsv` plus `manifest.json` (fetch time, per-source and per-pathogen counts, SHA-256, citations, `coord_source_counts`).

### Canonical columns (`VIRUS_RAW_COLUMNS`)

| Column | Meaning |
|--------|---------|
| `record_id` | Stable unique id within the unified extract (`{source}:{native_id}`) |
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

### Deduplication rules (implemented)

**INSDC-backed sources** (`ena_sequence`, `ena_read_run`, `bvbrc`, `pathoplexus`):

1. Normalize accession strings (trim; consistent case) and group by `accession` when present.
2. Else group by `sample_accession` when present (especially for runs / samples without a sequence accession), keyed with pathogen when multi-virus.
3. Within a group, **merge to the richest non-null metadata**: prefer non-null `lat`/`lon`, then `subnational_region`, then `collection_date`, then `host` / `isolation_source`. Prefer `coord_source=exact_gps` over `sample_backfill` over `none`.
4. Retain a deterministic primary `source` for the merged row (prefer `ena_sequence` when a sequence accession exists; else `ena_read_run`; else `bvbrc` / `pathoplexus` in that order unless another source alone provides coordinates).

**Outbreak / surveillance sources** (`empres_i`, `ecdc_atlas`):

1. Do **not** collapse into INSDC accession groups.
2. Key by native outbreak / event id when published; else by `(source, pathogen_name, nuts_id | lat/lon, collection_date)`.
3. Keep them as separate detection rows so sequence bias and clinical/outbreak reporting remain distinguishable via `source`.

**Keep filter (all sources):** retain rows with usable place and/or time after source-specific parsing (non-empty `country` / `nuts_id` / `(lat,lon)` **or** `collection_date`), with ENA sample backfill applied **before** the keep filter, then apply the merge rules above.

## Target virus taxonomy

Each target taxon is mapped to a VectorNet vector group so features can relate mosquito / tick / midge / sandfly presence to the matching pathogens. NCBI Taxonomy IDs were **live-verified** against ENA Portal `tax_tree(...)` counts (2026-11). Prefer ICTV binomial species nodes in `tax_ids` (supersets of legacy common-name IDs); keep `legacy_tax_ids` for BV-BRC lineage recall.

Authoritative code: [`src/vector_guard/data.py`](../src/vector_guard/data.py) `VIRUS_VECTOR_TAXON_MAP` (**26** pathogens).

### Implemented taxonomy (verified tax IDs)

| Pathogen (canonical name) | `tax_ids` (ENA / ICTV) | `legacy_tax_ids` | Vector group |
|---------------------------|------------------------|------------------|--------------|
| West Nile virus | `3048448` | `11082` | mosquito |
| Usutu virus | `3048443` | `64286` | mosquito |
| Dengue virus | `3052464` | `12637` | mosquito |
| Chikungunya virus | `3426298` | `37124` | mosquito |
| Zika virus | `3048459` | `64320` | mosquito |
| Sindbis virus | `3426318` | `11034` | mosquito |
| Rift Valley fever virus | `3052676` | `11588` | mosquito |
| Batai orthobunyavirus | `3052371` | `80942` | mosquito |
| Tahyna / California encephalitis orthobunyavirus | `3052445`, `35305`, `178787` | `45270` | mosquito |
| Inkoo orthobunyavirus | `45269` | — | mosquito |
| Japanese encephalitis virus | `3048158` | `11072` | mosquito |
| Yellow fever virus | `3046277` | `11089` | mosquito |
| Tick-borne encephalitis virus | `3052465` | `11084` | tick |
| Crimean-Congo hemorrhagic fever virus | `3052518` | — | tick |
| Louping ill virus | `3048184` | `11086` | tick |
| Omsk hemorrhagic fever virus | `3048233` | `12542` | tick |
| Thogoto / Bourbon thogotovirus | `11569`, `2956523` | `1618189` | tick |
| Jingmen tick virus | `1172985` | — | tick |
| Alongshan virus | `2269360` | — | tick |
| Bluetongue virus | `3431240` | `40051` | biting_midge |
| Schmallenberg virus | `3052437` | `1133363` | biting_midge |
| Epizootic hemorrhagic disease virus | `40054` | — | biting_midge |
| African horse sickness virus | `40050` | — | biting_midge |
| Akabane orthobunyavirus | `1933178` | `70566` | biting_midge |
| Sandfly fever Naples phlebovirus / Toscana virus | `3052686`, `3052666`, `1933189` | `11590`, `206160` | sandfly |
| Phlebovirus (Mediterranean sandfly fever complex) | `3052681`, `3052661`, `3052675`, `904668` | `28292` | sandfly |

### Tax ID corrections vs early indicative IDs

Early draft IDs in this spec pointed at wrong or obsolete taxa; the live-verified replacements are:

| Pathogen | Indicative (wrong / obsolete) | Verified |
|----------|-------------------------------|----------|
| Thogoto / Bourbon | `11320` (Influenza A, ~1.69M seq) | `11569`, `2956523` (+ legacy Bourbon `1618189`) |
| Batai | `11574` (Germiston) | `3052371` (+ legacy `80942`) |
| Tahyna | `11577` (La Crosse) | `3052445` (+ California complex) |
| Omsk | `11083` (Powassan) | `3048233` (+ legacy `12542`) |
| EHDV | `40050` (African horse sickness) | `40054` (EHDV); AHSV kept as `40050` |
| Akabane | `11572` (genus-level) | `1933178` (+ legacy `70566`) |
| Mediterranean phlebovirus broaden | `11584` (genus; includes mosquito-borne RVFV) | species-level Sicilian / Massilia / Punique / Granada IDs |

Keep tagging outbreak rows (`empres_i`, `ecdc_atlas`) with the same `pathogen_name` / `vector_group` vocabulary even when no NCBI tax ID is present on the source row.

### Extract implementation

[`notebooks/01_sources/03_extract_viruses.ipynb`](../notebooks/01_sources/03_extract_viruses.ipynb):

1. Wipe `data/01_raw/virus/` (preserve `.gitkeep`).
2. Fetch all six feeds; normalize into `VIRUS_RAW_COLUMNS`.
3. Apply INSDC + outbreak dedupe; assign stable `record_id`.
4. Write `virus_detections.tsv` + `manifest.json` (per-source / per-pathogen counts, citations, `coord_source_counts`).
5. Smoke-check via `load_virus_detections`.

Load in other notebooks:

```python
from vector_guard.data import load_virus_detections

df = load_virus_detections()
```

Cleaning, ISO-2, subnational centroid → H3, and panel merge remain owned by specs [`03`](03-spatial-temporal-matching-strategy.md) and [`04`](04-reference-data-and-panel-pipeline.md) (`09_clean_viruses`, `10_merge_modelling_panel`).

### Auxiliary signal from VectorNet

VectorNet’s `dynamicProperties` column sometimes embeds pathogen strings (e.g. `{"pathogen": "West Nile virus"}`). Those sparse rows are **not** part of the multi-source virus extract; they may be used later as an optional validation / enrichment signal during EDA or matching.

## Out of scope for this decision

- Spatial-temporal join implementation and subnational centroid promotion (design in [`specs/03-spatial-temporal-matching-strategy.md`](03-spatial-temporal-matching-strategy.md) and [`specs/04-reference-data-and-panel-pipeline.md`](04-reference-data-and-panel-pipeline.md))
- Clinical diagnosis or exact introduction-date prediction

## Related project files

| Path | Role |
|------|------|
| [`specs/01-vector-dataset-selection.md`](01-vector-dataset-selection.md) | Paired vector source (VectorNet) |
| [`specs/03-spatial-temporal-matching-strategy.md`](03-spatial-temporal-matching-strategy.md) | Join design (H3 + country; subnational Tier 1 path) |
| [`specs/04-reference-data-and-panel-pipeline.md`](04-reference-data-and-panel-pipeline.md) | Reference tables, virus clean/resolve, modelling panel |
| [`README.md`](../README.md) | Published virus data table and refresh steps |
| [`ROADMAP.md`](../ROADMAP.md) | Build status for multi-source extract / taxonomy |
| [`notebooks/01_sources/03_extract_viruses.ipynb`](../notebooks/01_sources/03_extract_viruses.ipynb) | Multi-source virus extract |
| [`notebooks/01_sources/04_inspect_viruses.ipynb`](../notebooks/01_sources/04_inspect_viruses.ipynb) | Virus source inspect (per-source, coord_source, NUTS3) |
| [`src/vector_guard/data.py`](../src/vector_guard/data.py) | `VIRUS_VECTOR_TAXON_MAP`, `load_virus_detections()` |
| [`src/vector_guard/virus_extract.py`](../src/vector_guard/virus_extract.py) | Unified schema + dedupe helpers |
