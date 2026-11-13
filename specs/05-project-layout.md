# Project layout

| Field | Value |
|-------|-------|
| Status | Decided |
| Date | 2026-11 |

## Decision

Organize the repository as a **generic ML project**:

1. **Root surface** — problem README, primary analysis notebook, training script, prediction service, container, dependency file.
2. **Upstream dataset construction** — when inputs are not a single ready table, build the modelling dataset under `notebooks/01_sources/` into `data/03_processed/`.
3. **Staged data** — `data/01_raw/` → `data/02_interim/` → `data/03_processed/`, plus `data/external/` for lookups.
4. **Staged notebooks** — `01_sources`, `02_eda`, `03_features`, `04_modeling`; primary EDA and modeling remain in root `notebook.ipynb`.

Dataset construction (multi-source fetch, inspect, clean, merge) maps to **Reproducibility** / Data. It is **not** the **EDA** criterion. EDA and model training apply to the modelling panel in `notebook.ipynb`.

## Tree

```text
vector-guard/
├── README.md
├── notebook.ipynb
├── train.py
├── predict.py
├── Dockerfile
├── pyproject.toml
├── data/
│   ├── 01_raw/
│   ├── 02_interim/
│   ├── 03_processed/
│   └── external/
├── notebooks/
│   ├── 01_sources/
│   ├── 02_eda/
│   ├── 03_features/
│   └── 04_modeling/
├── src/vector_guard/
├── specs/
└── deploy/
```

## Evaluation Criteria → location

| Criterion | Where |
|-----------|-------|
| Problem description | `README.md` § Problem description |
| EDA | `notebook.ipynb` only |
| Model training | `notebook.ipynb` |
| Exporting notebook to script | `train.py` |
| Reproducibility | `data/` + README Data/Setup; rebuild via `notebooks/01_sources/` |
| Model deployment | `predict.py` |
| Dependency and environment management | `pyproject.toml` + `uv.lock` + README Setup |
| Containerization | `Dockerfile` + README Deployment |
| Cloud deployment | `deploy/` + README Deployment (optional) |

## Related

- [`README.md`](../README.md) — mirrors this map for readers
- [`specs/04-reference-data-and-panel-pipeline.md`](04-reference-data-and-panel-pipeline.md) — panel build contract
