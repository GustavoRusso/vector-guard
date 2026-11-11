# Vector Guard

Predict geographic risk of vector-borne virus presence or outbreak from vector detections and related spatial-temporal context.

## Problem description

Vector-borne diseases (for example dengue, West Nile fever, Zika, or chikungunya) spread when competent vectors—such as mosquitoes or ticks—are present and environmental and ecological conditions allow transmission. As vectors expand into new areas and climate and land use change, public-health agencies need ways to prioritize surveillance and control before outbreaks become large.

Existing tools often fall into two categories:

1. **Suitability / outbreak risk** — Can this place support transmission *if* the pathogen is present? This is relatively tractable with entomological, environmental, and epidemiological signals.
2. **Exact introduction timing** — *When* will the virus first arrive at a given location? That is highly stochastic: it depends on rare human mobility events (for example an infected traveler) and is much harder to predict reliably.

**Vector Guard** focuses on the first problem. The project estimates a **risk score** (probability of suitability or outbreak risk) for geographic locations, including places where virus reports are sparse or absent, by relating vector presence patterns to virus detection patterns over space and time.

### How the solution will be used

The intended output is an **early-warning / prioritization aid** for surveillance and control planning:

- Flag locations with high estimated risk given observed vector activity
- Help compare relative risk across regions or time windows
- Support decisions on where to intensify trapping, testing, or outreach

It is **not** a clinical diagnostic tool and does not replace expert epidemiological judgment. Exact first-introduction dates are out of scope; the model targets risk of conditions that favor virus presence or outbreak potential.

## Intended approach

```mermaid
flowchart LR
  vectorData[Vector detections geo time]
  virusData[Virus detections geo time]
  features[Spatial temporal features]
  model[ML risk model]
  api[Prediction service]
  vectorData --> features
  virusData --> features
  features --> model
  model --> api
```

1. **Build two datasets** (both sources selected — see [Data](#data)):
   - **Vector detections** — taxon/species, geographic location, detection time
   - **Virus detections** — pathogen, geographic location, detection time
2. **Resolve and join** onto common keys using reference data (ISO-2 countries, vector_group maps) and Uber H3 where coordinates exist, with ISO-2 country fallback; temporal grain **`year` × `month`** — see [`specs/03-spatial-temporal-matching-strategy.md`](specs/03-spatial-temporal-matching-strategy.md) and [`specs/04-reference-data-and-panel-pipeline.md`](specs/04-reference-data-and-panel-pipeline.md).
3. **Merge** cleaned sides into one modelling panel under `data/processed/` (training units require VectorNet coverage).
4. **EDA** — missing values, spatial and temporal coverage, target distribution, and feature importance (on the panel for modelling).
5. **Model selection** — train multiple models (linear and tree-based), tune hyperparameters, and select the best performer.
6. **Deploy** — export training to a script, serve the final model via a web API, and run it locally in Docker (cloud deployment optional).

## Data

Decision records for source selection, join design, and the panel pipeline live under [`specs/`](specs/):

| Spec | Topic |
|------|-------|
| [`specs/01-vector-dataset-selection.md`](specs/01-vector-dataset-selection.md) | VectorNet DwC-A selection and discarded alternatives |
| [`specs/02-virus-dataset-selection.md`](specs/02-virus-dataset-selection.md) | ENA / INSDC selection, candidate comparison, target taxonomy |
| [`specs/03-spatial-temporal-matching-strategy.md`](specs/03-spatial-temporal-matching-strategy.md) | H3 Tier 1 + ISO-2 Tier 2 join design |
| [`specs/04-reference-data-and-panel-pipeline.md`](specs/04-reference-data-and-panel-pipeline.md) | Reference data, resolve steps, merge → modelling panel |

Data layout (ladder):

| Path | Role |
|------|------|
| `data/raw/` | Source extracts (VectorNet, ENA); not committed; refresh via extract notebooks |
| `data/reference/` | Master/lookup tables (countries, vector taxon → group); committed when built |
| `data/interim/` | Normalized per-side detection tables after cleaning |
| `data/processed/` | Merged **modelling panel** used by `notebook.ipynb` / `train.py` |

H3 cell IDs are computed from lat/lon at a resolution chosen in a density-check notebook (not a downloaded world H3 dump).

### Vector detections — VectorNet observations (selected)

| Field | Value |
|-------|-------|
| Dataset | [VectorNet observations](https://www.gbif.org/dataset/4abd984b-122c-44a0-8c92-b37e2f5299b1) (ECDC / EFSA) |
| GBIF UUID | `4abd984b-122c-44a0-8c92-b37e2f5299b1` |
| Format | Darwin Core Archive (DwC-A) |
| Latest download URL | `https://www.gbif.se/ipt/archive.do?r=vectornet_historical_data` |
| License | [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Local path | `data/raw/vector/` (not committed; re-fetched on demand) |
| Decision | [`specs/01-vector-dataset-selection.md`](specs/01-vector-dataset-selection.md) |

Refresh the local raw copy (wipes and replaces `data/raw/vector/`):

```bash
jupyter notebook notebooks/01_extract_vectors.ipynb
```

Then run all cells. The notebook writes `manifest.json` (fetch time, URL, SHA-256) next to the extracted archive.

Downstream notebooks load the table with the shared helper:

```python
from vector_guard.data import load_vector_detections

df = load_vector_detections()
```

### Virus detections — ENA / INSDC (selected)

| Field | Value |
|-------|-------|
| Dataset | [ENA Portal API](https://www.ebi.ac.uk/ena/portal/api/) (INSDC: ENA + GenBank + DDBJ) |
| Search endpoint | `https://www.ebi.ac.uk/ena/portal/api/search` |
| Result type | `result=sequence` (`tax_tree` per target pathogen) |
| Format | TSV metadata extract |
| License / terms | [EMBL-EBI Terms of Use](https://www.ebi.ac.uk/about/terms-of-use/) (no account required) |
| Local path | `data/raw/virus/` (not committed; re-fetched on demand) |
| Decision | [`specs/02-virus-dataset-selection.md`](specs/02-virus-dataset-selection.md) |

Twelve vector-borne pathogens are fetched (mosquito-, tick-, biting-midge-, and sandfly-borne), tagged with `pathogen_name` and `vector_group`. Taxonomy and ENA tax IDs are listed in the virus dataset spec and in `VIRUS_VECTOR_TAXON_MAP` in [`src/vector_guard/data.py`](src/vector_guard/data.py).

Refresh the local raw copy (wipes and replaces `data/raw/virus/`):

```bash
jupyter notebook notebooks/03_extract_viruses.ipynb
```

Then run all cells. The notebook writes `virus_detections.tsv` and `manifest.json` (fetch time, per-pathogen counts, SHA-256, citation).

Downstream notebooks load the table with the shared helper:

```python
from vector_guard.data import load_virus_detections

df = load_virus_detections()
```

Initial exploratory analysis: [`notebooks/04_eda_viruses.ipynb`](notebooks/04_eda_viruses.ipynb).

## Roadmap

See [`ROADMAP.md`](ROADMAP.md) for the planned features and build order (data, EDA, models, training script, API, environment, Docker, and optional cloud deploy).

## Planned project structure

| Path | Role |
|------|------|
| `src/vector_guard/` | Shared helpers (`load_vector_detections`, `load_virus_detections`, `VIRUS_VECTOR_TAXON_MAP`) |
| `notebooks/01_extract_vectors.ipynb` | Download latest VectorNet observations DwC-A and overwrite `data/raw/vector/` |
| `notebooks/02_eda_vectors.ipynb` | Exploratory analysis of the vector detections dataset |
| `notebooks/03_extract_viruses.ipynb` | Fetch ENA / INSDC virus metadata into `data/raw/virus/` |
| `notebooks/04_eda_viruses.ipynb` | Exploratory analysis of the virus detections dataset |
| `notebooks/05`–`10` (planned) | Reference tables, H3 density check, clean both sides, merge modelling panel — see spec `04` |
| `data/reference/`, `data/interim/`, `data/processed/` | Lookup tables, normalized sides, modelling panel (see [Data](#data)) |
| `specs/` | Decision records (dataset selection, matching strategy, panel pipeline) |
| `notebook.ipynb` | Model comparison and tuning (after panel build) |
| `train.py` | Train the final model and save it to disk |
| `predict.py` | Load the model and serve predictions via a web service |
| Dependency file (`requirements.txt`, `Pipfile`, or `pyproject.toml`) | Environment and package versions |
| `Dockerfile` | Container image for the prediction service |
| `docs/` | Early research notes (read-only; not the decision source of truth) |

## Setup

*Coming soon* — install dependencies and activate the virtual environment once the stack is finalized.

## Model training

*Coming soon* — how to run the notebook and `train.py`, including expected outputs (saved model artifact).

## Deployment

*Coming soon* — how to build and run the Docker image locally, example API requests, and (optionally) cloud or Kubernetes deployment notes with a test URL or screenshot.

## Reproducibility

*Coming soon* — steps to re-run the notebook and training script end-to-end once datasets and download instructions are published.
