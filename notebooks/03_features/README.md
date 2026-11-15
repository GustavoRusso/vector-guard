# Feature prep (`03_features`)

Panel cleaning / filters, locked unit-grain late priority species pivot (`priority_vector_taxa.csv` → `vector_count_<slug>`), and the modelling feature matrix handoff (`X` / `y`) for training.

**Inputs:** modelling panel + species side table from [`../01_sources/README.md`](../01_sources/README.md); closed set [`data/external/priority_vector_taxa.csv`](../../data/external/priority_vector_taxa.csv).

**Outputs / handoff:** cleaned analysis table and feature columns consumed by [`../04_modeling/`](../04_modeling/) and mirrored later in [`train.py`](../../train.py). Prefer shared helpers in `src/vector_guard/` (e.g. `panel_features.py`) over copy-pasted prep cells.

**Does not own:** descriptive EDA (`02_eda`), model selection write-up (`04_modeling`), merge/panel contract (`01_sources` / [`specs/04`](../../specs/04-reference-data-and-panel-pipeline.md)).

Layout and deliverable map: [`README.md`](../../README.md).

## Notebook sequence

| Notebook | Role |
|----------|------|
| *(pending)* | Panel prep filters + locked late priority pivot + feature matrix handoff |

See [`ROADMAP.md`](../../ROADMAP.md) § Exploratory data analysis for status. Contract for the late pivot: [`specs/04`](../../specs/04-reference-data-and-panel-pipeline.md).

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

## Next stage

Hand off features to [`../04_modeling/README.md`](../04_modeling/README.md).
