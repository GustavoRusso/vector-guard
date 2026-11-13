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

Dataset construction (multi-source fetch, inspect, clean, merge) maps to **Reproducibility** / Data. It is **not** the **EDA** deliverable area. EDA and model training apply to the modelling panel in `notebook.ipynb`.

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

## Deliverable areas → location

| Deliverable area | Where |
|------------------|-------|
| Problem description | `README.md` § Problem statement |
| EDA | `notebook.ipynb` only |
| Model training | `notebook.ipynb` |
| Exporting notebook to script | `train.py` |
| Reproducibility | `data/` + README Dataset description; rebuild via [`notebooks/01_sources/README.md`](../notebooks/01_sources/README.md) |
| Model deployment | `predict.py` |
| Dependency and environment management | `pyproject.toml` + `uv.lock` + README How to run locally and via Docker |
| Containerization | `Dockerfile` + README How to run locally and via Docker |
| Cloud deployment | `deploy/` + README How to run locally and via Docker (optional) |

## Related

- [`README.md`](../README.md) — mirrors this Deliverable areas map for readers (Problem statement, Dataset description, Architecture, EDA, Modeling, How to run, API, Limitations)
- [`notebooks/01_sources/README.md`](../notebooks/01_sources/README.md) — dataset construction runbook (regenerate panel; links specs `01`–`04`)
- [`specs/04-reference-data-and-panel-pipeline.md`](04-reference-data-and-panel-pipeline.md) — panel build contract
