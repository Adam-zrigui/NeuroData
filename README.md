# NeuroRAG

NeuroRAG is a research prototype for finding rodent fear-conditioning studies by experimental methods. It builds a small corpus from open-access Europe PMC articles, extracts study details from the methods text, and combines structured filters with vector similarity to rank relevant papers.

## What it does

- Searches Europe PMC for open-access papers about fear conditioning in mice and rats, then downloads available full-text XML.
- Extracts methods sections, article titles, and licence links from the XML.
- Uses an OpenRouter-compatible chat model to extract experimental details and turn natural-language requests into filters. Extracted values are checked against quoted source text; a rule-based query parser is available as a fallback.
- Stores papers, extracted fields, and 384-dimensional text embeddings in PostgreSQL with pgvector.
- Ranks matching papers and prints their metadata, source quotations, and Europe PMC links.

This repository contains research scripts and intermediate data workflows; it does not currently provide a web interface or a packaged command-line application.

## Requirements

- Python 3.10 or newer
- Docker Compose
- An OpenRouter API key for LLM-powered extraction and query parsing
- Enough memory and disk space for the `sentence-transformers/all-MiniLM-L6-v2` model and the paper corpus

Install the Python packages used by the scripts:

```bash
python -m pip install requests lxml python-dotenv openai pydantic "psycopg[binary]" pgvector sentence-transformers
```

## Configuration

Create a `.env` file in the project root (keep it private):

```dotenv
DB_PASSWORD=choose-a-local-database-password
OPENROUTER_API_KEY=your-openrouter-api-key
# Optional: query parser model; defaults to google/gemma-4-26b-a4b-it:free
QUERY_MODEL=google/gemma-4-26b-a4b-it:free
```

The extraction scripts also specify their model defaults in code. API usage, model availability, and rate limits depend on your OpenRouter account and the selected model.

## Intended workflow

Run the scripts from the repository root. Several steps expect the output of earlier steps and use fixed filenames.

1. Start PostgreSQL with pgvector:

   ```bash
   docker compose up -d db
   ```

2. Download article XML and create the paper/methods corpus:

   ```bash
   python download.py
   python parse.py
   ```

   These create `papers/` and `papers.json`.

3. Extract and verify experimental details. `extract.py` processes up to 100 papers per run and writes `extractions_qwen.json`; `clean.py` verifies available extractions and writes `clean_extractions.json`. `cue_pass.py` optionally classifies the conditioning cue.

   ```bash
   python extract.py
   python clean.py
   python cue_pass.py
   ```

4. Load papers and extractions, then embed methods chunks:

   ```bash
   python load.py
   python embed.py
   ```

5. Search using a natural-language request, or supply explicit filters and skip LLM parsing:

   ```bash
   python search.py "mouse fear conditioning with 0.6 mA shock and five pairings"
   python search.py "fear conditioning" --no-parse --species mouse --shock 0.6 --pairings 5
   ```

Useful optional search flags are `--species mouse|rat`, `--shock`, `--pairings`, `--tone`, and `--limit`.

## Database setup note

The current `init.sql` schema does not yet define every column referenced by `load.py` and `search.py` (including normalized species and scope fields, and tone-value arrays). As a result, the documented database load/search workflow requires reconciling the schema with those scripts before it will run end to end. The database container initializes `init.sql` only when its data volume is first created.

## Data and licensing

Downloaded articles and generated JSON files are local working data and are ignored by Git. Article availability and reuse terms are determined by each article's licence; check the recorded licence before redistributing article text. Search results include PMCIDs and licence links to help locate the source publications.

## Repository scripts

| Script | Purpose |
| --- | --- |
| `download.py`, `parse.py` | Fetch Europe PMC XML and extract article/methods metadata |
| `extract.py`, `clean.py`, `cue_pass.py` | Extract, verify, and optionally classify experimental parameters |
| `normalise.py`, `textutil.py` | Normalize values and verify quoted evidence |
| `load.py`, `embed.py`, `search.py` | Load PostgreSQL data, create embeddings, and search papers |
| `parse_query.py`, `scope.py` | Parse query filters and inspect out-of-scope records |
| `eval_parser.py`, `check.py` | Parser evaluation and extraction checks |

