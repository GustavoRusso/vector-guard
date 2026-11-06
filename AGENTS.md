# Agent conventions

## `docs/` — read-only insight

- Agents **may read** files under `docs/` for background on scope, sources, and early research.
- Agents **must not** create, edit, delete, rename, or move anything under `docs/`.
- `docs/` is **not** the project’s living documentation or source of truth for decisions. Do not add new project docs there, donot reference those documents from outside the docs/ folder and do not treat it as the place to record or update decisions.

## `specs/` — decision documentation

- Store documentation of **decisions taken** on the project in `specs/`.
- One document per **topic or project step** (for example dataset choice, geographic unit, model selection).
- When a decision is made or changed during work, record or update it in `specs/`, not in `docs/`.



## `notebooks/` — Jupyter notebooks with all ML steps



## `src/vector_guard` — reutilizable code for notebooks



## Related project files

| Path                       | Role                               |
| -------------------------- | ---------------------------------- |
| [`README.md`](README.md)   | Problem statement and intended use |
| [`ROADMAP.md`](ROADMAP.md) | Feature and deliverable plan       |

