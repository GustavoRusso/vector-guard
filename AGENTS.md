# Agent conventions

## ENVIRONMENT

- Use the DevContainer (`.devcontainer/`) to run Jupyter notebooks in VS Code / Cursor. Python **3.12+** in a project virtualenv (`.venv`); `postCreateCommand` runs `uv sync`.
- Prefer notebook work as notebook cells, each preceded by a markdown cell that states the step’s purpose.
- Dependencies live in `pyproject.toml`; install and lock with **uv** (`uv.lock`). Do not invent ad-hoc `requirements.txt` or unpinned one-off installs for project code.
- Resolve paths from the repo root via `vector_guard.data.find_repo_root` (notebooks may be opened from subfolders). Reusable helpers live in `src/vector_guard/` and are imported as `from vector_guard...`.
- Show tables, plots, and maps **inline** in the notebook (`display`, seaborn, Folium). Put reusable viz helpers in `src/vector_guard/viz.py` rather than duplicating chart code across cells.

## WORKING STYLE

- Before each code block, 2–3 lines on what you will do and why.
- Print every key number. Never invent results.
- Ask before adding a library.
- In every answer, list the files you created or changed.
- Do ONE step per answer and wait for me to say "next".
- If I say a rule is broken, redo only the affected code and keep everything else.

## Project structure

### `docs/` — read-only insight

- Agents **may read** files under `docs/` for background on scope, sources, and early research.
- Agents **must not** create, edit, delete, rename, or move anything under `docs/`.
- `docs/` is **not** the project’s living documentation or source of truth for decisions. Do not add new project docs there, do not reference those documents from outside the docs/ folder, and do not treat it as the place to record or update decisions.

### `specs/` — decision documentation

- Store documentation of **decisions taken** on the project in `specs/` (for example dataset choice, geographic unit, model selection).
- One document per **topic or project step**.
- When a decision is made or changed during work, record or update it in `specs/`, not in `docs/`.
- Repo layout and deliverable → path map live in [`README.md`](README.md), not in `specs/`.

## Documentation single source of truth

Each concept is **defined in exactly one** canonical document (or section). Other docs may **link** or use a one-line pointer; they must **not** restate the contract, decision table, or grain definition.

- Canonical doc **defines**. Non-canonical docs **link**.
- To change a concept, edit the canonical owner first; then fix links elsewhere if needed.
- `docs/` is never a living source of truth (see above).

| Concept | Canonical |
|---------|-----------|
| Problem statement / deliverable map / how to run | [`README.md`](README.md) |
| Feature / deliverable status | [`ROADMAP.md`](ROADMAP.md) |
| Vector source selection | [`specs/01-vector-dataset-selection.md`](specs/01-vector-dataset-selection.md) |
| Virus taxonomy / pathogen↔group | [`specs/02-virus-dataset-selection.md`](specs/02-virus-dataset-selection.md) (+ code `VIRUS_VECTOR_TAXON_MAP`) |
| Spatial-temporal join (tiers, Path A/B, A3) | [`specs/03-spatial-temporal-matching-strategy.md`](specs/03-spatial-temporal-matching-strategy.md) |
| Panel contract, H3 res, reference artifacts, pipeline | [`specs/04-reference-data-and-panel-pipeline.md`](specs/04-reference-data-and-panel-pipeline.md) |
| Stage how-to (commands, notebook order) | Matching `notebooks/*/README.md` only |

## Layout and deliverables

See [`README.md`](README.md) § Project layout and Deliverable areas → location.

- `notebooks/01_sources/` — dataset construction only (not the EDA deliverable). Runbook: [`notebooks/01_sources/README.md`](notebooks/01_sources/README.md).
- `notebooks/02_eda/` — EDA on the modelling panel. Runbook: [`notebooks/02_eda/README.md`](notebooks/02_eda/README.md).
- `notebooks/03_features/` — panel prep, locked late species pivot, feature handoff. Runbook: [`notebooks/03_features/README.md`](notebooks/03_features/README.md).
- `notebooks/04_modeling/` — train / tune / compare. Runbook: [`notebooks/04_modeling/README.md`](notebooks/04_modeling/README.md).
- Reusable notebook code: `src/vector_guard/` — import shared prep and viz helpers; do not duplicate them across stage notebooks.

## Related living docs

| Path | Role |
|------|------|
| [`README.md`](README.md) | Problem statement, layout, deliverable map, dataset pointer, run instructions |
| [`ROADMAP.md`](ROADMAP.md) | Feature and deliverable plan / status |
| [`notebooks/01_sources/README.md`](notebooks/01_sources/README.md) | Dataset construction runbook |
| [`notebooks/02_eda/README.md`](notebooks/02_eda/README.md) | EDA runbook |
| [`notebooks/03_features/README.md`](notebooks/03_features/README.md) | Feature prep runbook |
| [`notebooks/04_modeling/README.md`](notebooks/04_modeling/README.md) | Modeling runbook |
