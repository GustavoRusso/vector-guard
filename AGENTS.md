# Agent conventions

## `docs/` — read-only insight

- Agents **may read** files under `docs/` for background on scope, sources, and early research.
- Agents **must not** create, edit, delete, rename, or move anything under `docs/`.
- `docs/` is **not** the project’s living documentation or source of truth for decisions. Do not add new project docs there, do not reference those documents from outside the docs/ folder, and do not treat it as the place to record or update decisions.

## `specs/` — decision documentation

- Store documentation of **decisions taken** on the project in `specs/` (for example dataset choice, geographic unit, model selection).
- One document per **topic or project step**.
- When a decision is made or changed during work, record or update it in `specs/`, not in `docs/`.
- Repo layout and deliverable → path map live in [`README.md`](README.md), not in `specs/`.

## Layout and deliverables

See [`README.md`](README.md) § Project layout and Deliverable areas → location.

- `notebooks/01_sources/` — dataset construction only (not the EDA deliverable). Runbook: [`notebooks/01_sources/README.md`](notebooks/01_sources/README.md).
- Primary EDA and modeling: root `notebook.ipynb`.
- Reusable notebook code: `src/vector_guard/`.

## Related living docs

| Path | Role |
|------|------|
| [`README.md`](README.md) | Problem statement, layout, deliverable map, dataset pointer, run instructions |
| [`ROADMAP.md`](ROADMAP.md) | Feature and deliverable plan / status |
| [`notebooks/01_sources/README.md`](notebooks/01_sources/README.md) | Dataset construction runbook |
