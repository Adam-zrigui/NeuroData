# NeuroData Finder

NeuroData Finder helps students and small research groups find public neuroimaging datasets from a plain-language request, for example *"resting-state fMRI in adults over 60 with a motor task"*. The v1 scope is OpenNeuro MRI/fMRI metadata.

**How it works:** the request is parsed into visible, editable filters. Candidates are ranked with hybrid retrieval (PostgreSQL full-text plus pgvector similarity, merged with reciprocal rank fusion). Each result shows whether every stated requirement is `met`, `not_met` or `not_stated`, with source evidence where available.

**Design choices:**
- Metadata only. No imaging files are downloaded, stored or served.
- LLM extraction keeps a value only when the model returns an exact quote found in the source text; otherwise the field stays `not_stated`.
- Results are suggestions. Read the source dataset's documentation before relying on a match.

**Status:** the pipeline, API and demo UI run end to end. A human-judged evaluation set is not yet included, so no retrieval metrics are reported (see "Evaluation and release status").

## Current workflow

The existing root-level Python scripts form the workflow:

1. `download.py` harvests public OpenNeuro GraphQL metadata into a local cache and `openneuro_raw.json`.
2. `parse.py` normalizes the records and keeps MRI/fMRI datasets in `datasets.json`.
3. `extract.py` optionally asks an OpenRouter model to fill missing fields from available text. A value is kept only when the model returns an exact source quote. It is capped at 20 dataset calls per run by default and saves a progress file. With no API key, fields stay not stated.
4. `load.py` idempotently upserts metadata into PostgreSQL; `embed.py` creates local text embeddings.
5. `search.py` exposes a development CLI. `api.py` exposes `/health`, `/stats`, `/parse`, and `/search` through FastAPI.

OpenNeuro's official API documentation describes its public GraphQL endpoint for searching datasets and querying dataset/snapshot metadata. This project uses that API and caches responses to limit repeated requests: [OpenNeuro API examples](https://docs.openneuro.org/api.html).

## Setup

Requirements: Python 3.11+, Docker Compose, and the dependencies listed in `requirements.txt`.

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `DB_PASSWORD` in `.env` if you do not want the local development default. `OPENROUTER_API_KEY` is optional; it enables LLM extraction and natural-language filter parsing. Keep `.env` private.

Start the database and create the schema:

```bash
docker compose up -d db
python database.py
```

The database remains on the named `pgdata` volume. Schema initialization is idempotent and does not delete existing database contents.

## Index and search

```bash
python download.py
python parse.py
python extract.py       # optional; needs OPENROUTER_API_KEY
python load.py
python embed.py
python search.py "resting-state fMRI in adults over 60 with a motor task"
```

Use a small initial harvest while developing:

```powershell
$env:OPENNEURO_LIMIT = "25"
python download.py
```

The GraphQL responses are cached under `.cache/openneuro`. Set `OPENNEURO_REFRESH=1` to refresh cached pages. `OPENNEURO_LIMIT` limits a harvest, and `OPENNEURO_REQUEST_DELAY` controls the delay between network requests.

To make the parsed filters explicit and editable, pass a JSON file to `--filters`:

```json
{
  "modalities": ["fmri"],
  "species": "human",
  "population": null,
  "min_participants": null,
  "min_age": 60,
  "max_age": null,
  "tasks": ["motor"],
  "longitudinal": null,
  "resting_state": true,
  "processed_data_available": null,
  "field_strength": null
}
```

```bash
python search.py "resting-state fMRI over age 60" --filters my_filters.json
```

Run the API locally:

```bash
uvicorn api:app --reload
```

Open `http://127.0.0.1:8000/docs` to try the request and search endpoints. The `filters` value in `/search` can be edited by the caller before submitting.

Run the in-repository Next.js demo in another terminal (Node.js 20.9 or newer):

```bash
cd web
pnpm install
pnpm dev
```

Open `http://localhost:3000`. The client calls the FastAPI service at `http://127.0.0.1:8000`; set `NEXT_PUBLIC_API_URL` in `web/.env.local` if the API uses another address. The browser UI shows parsed filters, lets you edit the filter JSON, and displays result evidence. Next.js installation requirements are documented by [Next.js](https://nextjs.org/docs/app/getting-started/installation).

## Search and evidence behavior

- Search combines PostgreSQL full-text ranking and cosine similarity with reciprocal rank fusion.
- Structured metadata is retained as source fields when OpenNeuro supplies it; extraction does not fill unknowns by guessing.
- Each extracted field stores its value, status (`stated`, `inferred`, or `not_stated`), and evidence text. Current extraction accepts only quoted evidence that appears verbatim in the supplied metadata text.
- Parsed filters are returned before searching and can be overridden by the user or client.
- The result explanation reports `met`, `not_met`, and `not_stated` for each requested criterion.
- Dataset licence, repository ID, URL, and DOI are retained and shown with results when available.
- Search request text and caller identifiers are not stored. During harvesting, participant IDs and row-level ages are discarded after reducing them to a participant count and age range.

## Evaluation and release status

`eval_search.py` compares filters-only, keyword-only, vector-only, and hybrid rankings using a human-judged `eval_set.json`. Each entry has a query and a `relevant_dataset_ids` list. It reports precision@10, recall@10, and MRR. Create and review a dataset-specific labeled set before using these metrics as project results. The existing `label_sheet.py`, `labels.csv`, and `score.py` are from the earlier paper-search experiment; their labels are not OpenNeuro relevance judgments.

User interviews, five real search baselines, hand-checking 150 datasets, outside relevance judgments, and OpenNeuro's metadata reuse terms remain validation tasks from the design plan. The repository does not claim those tasks are complete.

## Configuration

Copy `.env.example` to `.env` and configure as needed:

| Variable | Purpose |
| --- | --- |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Local PostgreSQL connection |
| `DATABASE_URL` | Optional full PostgreSQL connection string |
| `OPENNEURO_ENDPOINT` | GraphQL endpoint; defaults to `https://openneuro.org/crn/graphql` |
| `OPENNEURO_CACHE_DIR` | Cached GraphQL responses |
| `OPENNEURO_LIMIT` | Optional maximum number of datasets per harvest |
| `OPENNEURO_REQUEST_DELAY`, `OPENNEURO_REFRESH` | Request delay and optional refresh of cached GraphQL pages |
| `OPENROUTER_API_KEY` | Optional model access for request parsing and gap extraction |
| `QUERY_MODEL`, `LLM_MODEL`, `LLM_EXTRACTION_LIMIT` | Model choices and per-run extraction-call cap |
| `EMBEDDING_MODEL` | Local sentence-transformers embedding model |
| `CORS_ORIGINS` | Comma-separated browser origins allowed by the local API |

## Data model

Each normalized dataset contains `dataset_id`, repository, title, URL, description, licence, DOI, and evidence-backed values for modalities, species, population, participant count, age range, longitudinal status, tasks, resting-state, processed data, field strength, and paper DOI. Dataset fields are stored in the `datasets` table. No raw imaging files are fetched.

`init.sql` retains the earlier literature-search tables for local data compatibility while adding the dataset table and search indexes. The root-level scripts remain the project entry points; `papers/`, extracted paper JSON, OpenNeuro cache data, and normalized datasets are local artifacts ignored by Git.

OpenNeuro's [metadata reuse policy](https://docs.openneuro.org/policy/general.html) states that public metadata records are CC0 and may be harvested. Individual dataset files are governed by their own recorded licence; this project does not copy or serve those files.

The paper-specific `clean.py`, `cue_pass.py`, `check.py`, `eval_parser.py`, `scope.py`, `textutil.py`, `label_sheet.py`, and `score.py` are retained as research history. The active v1 dataset workflow is the OpenNeuro pipeline documented above; paper labels are not used by dataset search or evaluation.
