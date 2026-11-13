# Agent conventions

## `docs/` — read-only insight

- Agents **may read** files under `docs/` for background on scope, sources, and early research.
- Agents **must not** create, edit, delete, rename, or move anything under `docs/`.
- `docs/` is **not** the project’s living documentation or source of truth for decisions. Do not add new project docs there, do not reference those documents from outside the docs/ folder, and do not treat it as the place to record or update decisions.

## `specs/` — decision documentation

- Store documentation of **decisions taken** on the project in `specs/`.
- One document per **topic or project step** (for example dataset choice, geographic unit, model selection, project layout).
- When a decision is made or changed during work, record or update it in `specs/`, not in `docs/`.

## `notebooks/` — staged Jupyter work

- `notebooks/01_sources/` — dataset construction (extract, inspect, clean, merge). Not the EDA Evaluation Criterion.
- `notebooks/02_eda/`, `03_features/`, `04_modeling/` — optional drafts; primary EDA and modeling live in root `notebook.ipynb`.

## `data/` — staged data ladder

- `data/01_raw/` → `data/02_interim/` → `data/03_processed/` (modelling panel handoff)
- `data/external/` — committed lookup / dictionary tables

## `src/vector_guard` — reusable code for notebooks

## Related project files

| Path | Role |
|------|------|
| [`README.md`](README.md) | Problem statement, Evaluation Criteria map, run instructions |
| [`ROADMAP.md`](ROADMAP.md) | Feature and deliverable plan |
| [`specs/05-project-layout.md`](specs/05-project-layout.md) | Layout decision and criteria→path map |
