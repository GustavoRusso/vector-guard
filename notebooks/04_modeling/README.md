# Model training (`04_modeling`)

Train, tune, and compare candidate models on the feature handoff from `03_features`. Document metrics and selection rationale here; export the final pipeline via [`train.py`](../../train.py).

**Inputs:** cleaned panel / feature matrix from [`../03_features/README.md`](../03_features/README.md) (panel + species table + locked late priority pivot).

**Outputs / handoff:** chosen model definition and metrics → [`train.py`](../../train.py) → [`predict.py`](../../predict.py).

**Does not own:** raw extract / merge (`01_sources`), descriptive EDA (`02_eda`), late pivot contract implementation (`03_features` / `src/vector_guard/`).

Layout and deliverable map: [`README.md`](../../README.md).

## Notebook sequence

| Notebook | Role |
|----------|------|
| *(pending)* | Baseline linear + tree-based models, hyperparameter tuning, comparison metrics |

See [`ROADMAP.md`](../../ROADMAP.md) § Model training and selection for status.

## Load pattern

Prefer loading the prepared feature matrix from the `03_features` handoff (or rebuilding it with the same helpers in `src/vector_guard/`). Panel load sketch:

```python
from pathlib import Path
import pandas as pd
from vector_guard.data import default_processed_dir, find_repo_root

REPO_ROOT = find_repo_root(Path.cwd())
PROCESSED = default_processed_dir(REPO_ROOT)
panel = pd.read_parquet(PROCESSED / "modelling_panel.parquet")
species = pd.read_parquet(PROCESSED / "modelling_panel_species.parquet")
```

## Next step

Once a model is selected, implement end-to-end training in [`train.py`](../../train.py).
