# Dataset construction (`01_sources`)

Rebuild the modelling panel used by root [`notebook.ipynb`](../../notebook.ipynb) and [`train.py`](../../train.py).

**Output:** [`data/03_processed/modelling_panel.parquet`](../../data/03_processed/) (+ `modelling_panel_manifest.json`).

This folder supports **Reproducibility** / Data. It is **not** the EDA deliverable area — EDA and model training use the panel in root `notebook.ipynb`.

Design decisions live in [`specs/`](../../specs/). Do not invent join rules, schemas, or pipeline contracts here; update the relevant spec when a decision changes.

## Specs (authority)

| Spec | Topic |
|------|-------|
| [`specs/01`](../../specs/01-vector-dataset-selection.md) | VectorNet source |
| [`specs/02`](../../specs/02-virus-dataset-selection.md) | Multi-source virus extract |
| [`specs/03`](../../specs/03-spatial-temporal-matching-strategy.md) | Spatial–temporal join |
| [`specs/04`](../../specs/04-reference-data-and-panel-pipeline.md) | Reference data, resolve, panel contract ([Panel columns](../../specs/04-reference-data-and-panel-pipeline.md#panel-columns)) |
| [`README.md`](../../README.md) | Repo layout / deliverable → path map |

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
| [`07_h3_resolution_density.ipynb`](07_h3_resolution_density.ipynb) | H3 resolution density check | Decision recorded in [`specs/04`](../../specs/04-reference-data-and-panel-pipeline.md) (`H3_RESOLUTION=4`) |
| [`08_clean_vectors.ipynb`](08_clean_vectors.ipynb) | Normalize vectors | `data/02_interim/vectors_normalized.parquet` |
| [`09_clean_viruses.ipynb`](09_clean_viruses.ipynb) | Normalize viruses | `data/02_interim/viruses_normalized.parquet` |
| [`10_merge_modelling_panel.ipynb`](10_merge_modelling_panel.ipynb) | Merge supervised panel | `data/03_processed/modelling_panel.parquet` + `modelling_panel_manifest.json` |

## Refresh raw extracts

Raw extracts under `data/01_raw/` are not committed. Source URLs, licenses, and schema: [`specs/01`](../../specs/01-vector-dataset-selection.md) (vectors), [`specs/02`](../../specs/02-virus-dataset-selection.md) (viruses).

```bash
# Wipes and replaces data/01_raw/vector/
jupyter notebook notebooks/01_sources/01_extract_vectors.ipynb

# Wipes and replaces data/01_raw/virus/
jupyter notebook notebooks/01_sources/03_extract_viruses.ipynb
```

Run all cells in each notebook. Loaders:

```python
from vector_guard.data import load_vector_detections, load_virus_detections

vectors = load_vector_detections()
viruses = load_virus_detections()
```

## Rebuild the modelling panel end-to-end

1. Refresh raw extracts (`01`, `03`) if sources changed.
2. Refresh reference tables (`05`, `06`) if aliases or taxon maps changed.
3. Re-run clean steps (`08`, `09`), then merge (`10`).
4. Confirm `data/03_processed/modelling_panel.parquet` exists, then open root `notebook.ipynb`.

How to load the panel: root [`README.md`](../../README.md) Dataset section and [`notebook.ipynb`](../../notebook.ipynb).
