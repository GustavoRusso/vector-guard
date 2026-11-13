# Dataset construction (`01_sources`)

Build and regenerate the modelling panel used by root [`notebook.ipynb`](../../notebook.ipynb) and [`train.py`](../../train.py).

**Output:** [`data/03_processed/modelling_panel.parquet`](../../data/03_processed/) (+ `modelling_panel_manifest.json`).

This folder supports **Reproducibility** / Data. It is **not** the EDA deliverable area — EDA and model training analyse the panel in root `notebook.ipynb`.

Design decisions live in [`specs/`](../../specs/). Do not invent join rules, schemas, or pipeline contracts here; update the relevant spec when a decision changes.

## Pipeline

```text
notebooks/01_sources/  →  data/02_interim/  →  data/03_processed/modelling_panel.parquet
                                                      ↓
                                              notebook.ipynb → train.py → predict.py
```

1. **Extract** vector and virus detections into `data/01_raw/`.
2. **Inspect** (construction QA), build **reference** lookups under `data/external/`, choose **H3** resolution.
3. **Clean** each side into `data/02_interim/`.
4. **Merge** into the modelling panel under `data/03_processed/` (training units require VectorNet coverage).

Spatial–temporal join summary: Tier 1 uses Uber H3 from exact GPS **or** curated admin centroids; Tier 2 falls back to ISO-2 country. Temporal grain is **`year` × `month`**. Details: specs [`03`](../../specs/03-spatial-temporal-matching-strategy.md) and [`04`](../../specs/04-reference-data-and-panel-pipeline.md).

## Design specs (authority)

| Spec | Topic |
|------|-------|
| [`specs/01-vector-dataset-selection.md`](../../specs/01-vector-dataset-selection.md) | VectorNet DwC-A selection and discarded alternatives |
| [`specs/02-virus-dataset-selection.md`](../../specs/02-virus-dataset-selection.md) | Multi-source virus strategy, unified schema, expanded taxonomy |
| [`specs/03-spatial-temporal-matching-strategy.md`](../../specs/03-spatial-temporal-matching-strategy.md) | H3 Tier 1 (GPS or subnational centroids) + ISO-2 Tier 2 |
| [`specs/04-reference-data-and-panel-pipeline.md`](../../specs/04-reference-data-and-panel-pipeline.md) | External lookups, resolve steps, merge → modelling panel ([Panel columns](../../specs/04-reference-data-and-panel-pipeline.md#panel-columns)) |

## Data ladder

| Path | Role |
|------|------|
| `data/01_raw/` | Source extracts (VectorNet, multi-source virus TSV); not committed; refresh via notebooks below |
| `data/external/` | Lookup tables (`countries.csv`, `subnational_locations.csv`, `vector_taxon_groups.csv`); committed |
| `data/02_interim/` | Normalized per-side detection tables after cleaning |
| `data/03_processed/` | Merged **modelling panel** used by `notebook.ipynb` / `train.py` |

H3 cell IDs are computed from lat/lon (exact GPS or curated subnational / NUTS3 centroids) at **`H3_RESOLUTION=4`** (chosen in `07_h3_resolution_density.ipynb`; not a downloaded world H3 dump).

To locate an `h3_cell` value on a map manually, paste the cell ID into the [H3 Viewer](https://clupasq.github.io/h3-viewer/).

## Notebook sequence

Run in order when rebuilding from scratch (or re-run from the step that changed):

| Notebook | Role | Typical outputs |
|----------|------|-----------------|
| [`01_extract_vectors.ipynb`](01_extract_vectors.ipynb) | Fetch VectorNet DwC-A | `data/01_raw/vector/` + `manifest.json` |
| [`02_inspect_vectors.ipynb`](02_inspect_vectors.ipynb) | Vector construction QA | — |
| [`03_extract_viruses.ipynb`](03_extract_viruses.ipynb) | Multi-source virus extract | `data/01_raw/virus/virus_detections.tsv` + `manifest.json` |
| [`04_inspect_viruses.ipynb`](04_inspect_viruses.ipynb) | Virus construction QA | — |
| [`05_reference_countries.ipynb`](05_reference_countries.ipynb) | Countries + subnational centroids | `data/external/countries.csv`, `subnational_locations.csv` |
| [`06_reference_vector_groups.ipynb`](06_reference_vector_groups.ipynb) | Taxon → `vector_group` | `data/external/vector_taxon_groups.csv` |
| [`07_h3_resolution_density.ipynb`](07_h3_resolution_density.ipynb) | Choose H3 resolution | Decision recorded as `H3_RESOLUTION=4` |
| [`08_clean_vectors.ipynb`](08_clean_vectors.ipynb) | Normalize vectors | `data/02_interim/vectors_normalized.parquet` |
| [`09_clean_viruses.ipynb`](09_clean_viruses.ipynb) | Normalize viruses | `data/02_interim/viruses_normalized.parquet` |
| [`10_merge_modelling_panel.ipynb`](10_merge_modelling_panel.ipynb) | Merge supervised panel | `data/03_processed/modelling_panel.parquet` + `modelling_panel_manifest.json` |

## Refresh raw extracts

### Vector detections — VectorNet observations

| Field | Value |
|-------|-------|
| Dataset | [VectorNet observations](https://www.gbif.org/dataset/4abd984b-122c-44a0-8c92-b37e2f5299b1) (ECDC / EFSA) |
| GBIF UUID | `4abd984b-122c-44a0-8c92-b37e2f5299b1` |
| Format | Darwin Core Archive (DwC-A) |
| Latest download URL | `https://www.gbif.se/ipt/archive.do?r=vectornet_historical_data` |
| License | [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Local path | `data/01_raw/vector/` (not committed; re-fetched on demand) |
| Decision | [`specs/01-vector-dataset-selection.md`](../../specs/01-vector-dataset-selection.md) |

Refresh the local raw copy (wipes and replaces `data/01_raw/vector/`):

```bash
jupyter notebook notebooks/01_sources/01_extract_vectors.ipynb
```

Then run all cells. The notebook writes `manifest.json` (fetch time, URL, SHA-256) next to the extracted archive.

Downstream notebooks load the table with the shared helper:

```python
from vector_guard.data import load_vector_detections

df = load_vector_detections()
```

### Virus detections — multi-source extract

| Field | Value |
|-------|-------|
| Strategy | Unified multi-source extract into `virus_detections.tsv` — see [`specs/02-virus-dataset-selection.md`](../../specs/02-virus-dataset-selection.md) |
| Feeds | [ENA Portal](https://www.ebi.ac.uk/ena/portal/api/) `sequence` + `read_run` + `sample` backfill; [BV-BRC Genome API](https://www.bv-brc.org/api/genome/); [Pathoplexus LAPIS](https://lapis.pathoplexus.org/); FAO EMPRES-i BigQuery CSV; ECDC WNV weekly/monthly NUTS3 |
| Format | Unified 19-column TSV metadata extract |
| Local path | `data/01_raw/virus/` (not committed; re-fetched on demand) |
| Decision | [`specs/02-virus-dataset-selection.md`](../../specs/02-virus-dataset-selection.md) |

**Taxonomy:** twenty-six vector-borne pathogens (mosquito-, tick-, biting-midge-, and sandfly-borne), tagged with `pathogen_name` and `vector_group`. Live-verified NCBI / ICTV tax IDs live in [`src/vector_guard/data.py`](../../src/vector_guard/data.py) (`VIRUS_VECTOR_TAXON_MAP`).

Refresh the local raw copy (wipes and replaces `data/01_raw/virus/`):

```bash
jupyter notebook notebooks/01_sources/03_extract_viruses.ipynb
```

Then run all cells. The notebook writes the unified `virus_detections.tsv` and `manifest.json` (fetch time, per-source and per-pathogen counts, SHA-256, citations, `coord_source_counts`).

Downstream notebooks load the table with the shared helper:

```python
from vector_guard.data import load_virus_detections

df = load_virus_detections()
```

Source inspection (dataset construction QA): [`04_inspect_viruses.ipynb`](04_inspect_viruses.ipynb).

## Rebuild the modelling panel end-to-end

1. Refresh raw extracts (`01`, `03`) if sources changed.
2. Refresh reference tables (`05`, `06`) if aliases or taxon maps changed.
3. Re-run clean steps (`08`, `09`), then merge (`10`).
4. Confirm `data/03_processed/modelling_panel.parquet` exists, then open root `notebook.ipynb`.

How to load the final panel for analysis is documented in root [`notebook.ipynb`](../../notebook.ipynb) and the root [`README.md`](../../README.md) Dataset section.
