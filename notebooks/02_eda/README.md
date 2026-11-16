# Exploratory data analysis (`02_eda`)

Descriptive analysis on the modelling panel + species side table: distributions, missingness, target balance, spatial/temporal coverage plots.

**Inputs:** [`data/03_processed/modelling_panel.parquet`](../../data/03_processed/) + [`modelling_panel_species.parquet`](../../data/03_processed/) (rebuild via [`../01_sources/README.md`](../01_sources/README.md)).

**Does not own:** dataset construction (`01_sources`), locked late priority pivot / feature matrix (`03_features`), model train/tune (`04_modeling`). Source-inspect notebooks under `01_sources` (`02`, `04`) are construction QA only — not this deliverable.

Layout and deliverable map: [`README.md`](../../README.md).

## Notebook sequence

| Notebook | Role |
|----------|------|
| [`panel_eda.ipynb`](panel_eda.ipynb) | Panel profile, target rates, missingness, effort-proxy outliers |

Add further notebooks here for feature-range plots, deeper target analysis, and spatial/temporal plots as they land ([`ROADMAP.md`](../../ROADMAP.md) § Exploratory data analysis).

## Load the panel

```python
from pathlib import Path
import pandas as pd
from vector_guard.data import default_processed_dir, find_repo_root

REPO_ROOT = find_repo_root(Path.cwd())
PROCESSED = default_processed_dir(REPO_ROOT)
panel = pd.read_parquet(PROCESSED / "modelling_panel.parquet")
species = pd.read_parquet(PROCESSED / "modelling_panel_species.parquet")
```

Reuse helpers from `src/vector_guard/` (especially `viz.py`); do not copy chart or load boilerplate across notebooks.

## Next stage

After EDA findings are clear, continue with feature prep under [`../03_features/README.md`](../03_features/README.md).
