# Dataset construction (`01_sources`)

Rebuild the modelling panel used by staged analysis notebooks (`02_eda` → `03_features` → `04_modeling`) and [`train.py`](../../train.py).

**Output:** [`data/03_processed/modelling_panel.parquet`](../../data/03_processed/) + [`modelling_panel_species.parquet`](../../data/03_processed/) (+ `modelling_panel_manifest.json`).

Panel grain, labels, and species side table: [`specs/04`](../../specs/04-reference-data-and-panel-pipeline.md) ([Panel columns](../../specs/04-reference-data-and-panel-pipeline.md#panel-columns)).

This folder supports **Reproducibility** / Data. It is **not** the EDA deliverable area — EDA, feature prep, and model training use the panel (+ species table) under `notebooks/02_eda/`, `03_features/`, and `04_modeling/`.

Design decisions live in [`specs/`](../../specs/). Do not invent join rules, schemas, or pipeline contracts here; update the relevant spec when a decision changes.

## Specs (authority)

| Spec | Topic |
|------|-------|
| [`specs/01`](../../specs/01-vector-dataset-selection.md) | Vector sources (VectorNet primary + SPVECTORSURV secondary) |
| [`specs/02`](../../specs/02-virus-dataset-selection.md) | Multi-source virus extract |
| [`specs/03`](../../specs/03-spatial-temporal-matching-strategy.md) | Spatial–temporal join |
| [`specs/04`](../../specs/04-reference-data-and-panel-pipeline.md) | Reference data, resolve, panel contract ([Panel columns](../../specs/04-reference-data-and-panel-pipeline.md#panel-columns)) |
| [`README.md`](../../README.md) | Repo layout / deliverable → path map |

## Notebook sequence

Run in order when rebuilding from scratch (or re-run from the step that changed):

| Notebook | Role | Typical outputs |
|----------|------|-----------------|
| [`01_extract_vectors.ipynb`](01_extract_vectors.ipynb) | Fetch VectorNet DwC-A | `data/01_raw/vector/` + `manifest.json` |
| [`01b_extract_spvectorsurv.ipynb`](01b_extract_spvectorsurv.ipynb) | Fetch SPVECTORSURV DwC-A (Spain densifier) | `data/01_raw/vector_spvectorsurv/` + `manifest.json` |
| [`02_inspect_vectors.ipynb`](02_inspect_vectors.ipynb) | Vector construction QA | — |
| [`03_extract_viruses.ipynb`](03_extract_viruses.ipynb) | Multi-source virus extract | `data/01_raw/virus/virus_detections.tsv` + `manifest.json` |
| [`04_inspect_viruses.ipynb`](04_inspect_viruses.ipynb) | Virus construction QA | — |
| [`05_reference_countries.ipynb`](05_reference_countries.ipynb) | Countries + subnational centroids | `data/external/countries.csv`, `subnational_locations.csv` |
| [`06_reference_vector_groups.ipynb`](06_reference_vector_groups.ipynb) | Taxon → `vector_group` (both vector sources); pathogen mirror; priority taxa (**EDA/prep** closed set) | `vector_taxon_groups.csv`, `pathogen_vector_group.csv`, `priority_vector_taxa.csv` |
| [`06b_reference_host_groups.ipynb`](06b_reference_host_groups.ipynb) | Host → `host_group` aliases | `data/external/host_groups.csv` |
| [`07_h3_resolution_density.ipynb`](07_h3_resolution_density.ipynb) | H3 resolution density check | Decision recorded in [`specs/04`](../../specs/04-reference-data-and-panel-pipeline.md) (`H3_RESOLUTION=4`) |
| [`08_clean_vectors.ipynb`](08_clean_vectors.ipynb) | Normalize + union vectors (`source` tag) | `data/02_interim/vectors_normalized.parquet` |
| [`08b-vector_h3_coverage.ipynb`](08b-vector_h3_coverage.ipynb) | Vector H3 / spatial coverage exploration |
| [`08c-vectors-source-visualization.ipynb`](08c-vectors-source-visualization.ipynb) | Interim vector source / effort visualization |
| [`08d_aggregate_vectors_species_monthly.ipynb`](08d_aggregate_vectors_species_monthly.ipynb) | H3 × month × species effort aggregate | `data/03_processed/vectors_species_monthly.parquet` |
| [`09_clean_viruses.ipynb`](09_clean_viruses.ipynb) | Normalize viruses (incl. `host_group`) | `viruses_normalized.parquet`; `virus_unmatched_regions.csv`; `virus_unmatched_hosts.csv` |
| [`09b-virus_h3_coverage.ipynb`](virus_h3_coverage.ipynb) | Virus H3 / spatial coverage exploration |
| [`09c-viruses-source-visualization.ipynb`](09c-viruses-source-visualization.ipynb) | Interim virus source visualization |
| [`09d_aggregate_virus_monthly.ipynb`](09d_aggregate_virus_monthly.ipynb) | H3 × month × pathogen × host aggregate | `data/03_processed/virus_monthly.parquet` |
| [`10_merge_modelling_panel.ipynb`](10_merge_modelling_panel.ipynb) | Merge supervised panel + species side table | `modelling_panel.parquet` + `modelling_panel_species.parquet` + `modelling_panel_manifest.json` |

## Refresh raw extracts

Raw extracts under `data/01_raw/` are not committed. Source URLs, licenses, and schema: [`specs/01`](../../specs/01-vector-dataset-selection.md) (vectors), [`specs/02`](../../specs/02-virus-dataset-selection.md) (viruses).

```bash
# Wipes and replaces data/01_raw/vector/
jupyter notebook notebooks/01_sources/01_extract_vectors.ipynb

# Wipes and replaces data/01_raw/vector_spvectorsurv/ only (VectorNet untouched)
jupyter notebook notebooks/01_sources/01b_extract_spvectorsurv.ipynb

# Wipes and replaces data/01_raw/virus/
jupyter notebook notebooks/01_sources/03_extract_viruses.ipynb
```

Run all cells in each notebook. Loaders:

```python
from vector_guard.data import (
    load_all_vector_detections,
    load_spvectorsurv_detections,
    load_vector_detections,
    load_virus_detections,
)

vectornet = load_vector_detections()
spvectorsurv = load_spvectorsurv_detections()
vectors = load_all_vector_detections()  # both, with source
viruses = load_virus_detections()
```

## Rebuild the modelling panel end-to-end

1. Refresh raw extracts (`01`, `01b`, `03`) if sources changed.
2. Refresh reference tables (`05`, `06`, `06b`) if country/region aliases, taxon maps, or host → `host_group` aliases changed.
3. Re-run clean steps (`08`, `09`), then merge (`10`). Optionally run `08d` after `08` for `vectors_species_monthly.parquet`, and `09d` after `09` for `virus_monthly.parquet`. (`08` unions VectorNet + SPVECTORSURV with `source`; `09` applies `host_groups.csv`; merge does not consume `host_group` yet.)
4. Confirm `data/03_processed/modelling_panel.parquet` and `modelling_panel_species.parquet` exist, then open [`../02_eda/`](../02_eda/) (then [`03_features`](../03_features/), [`04_modeling`](../04_modeling/)).

How to load the panel / species table: root [`README.md`](../../README.md) Dataset section and stage runbooks under `02_eda` / `03_features`.
