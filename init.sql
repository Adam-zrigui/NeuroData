CREATE EXTENSION IF NOT EXISTS vector;

-- Dataset metadata only. The application stores no downloaded imaging files.
CREATE TABLE IF NOT EXISTS datasets (
  dataset_id text PRIMARY KEY,
  repository text NOT NULL DEFAULT 'OpenNeuro',
  title text NOT NULL,
  url text NOT NULL,
  description text NOT NULL DEFAULT '',
  licence text,
  doi text,
  fields jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  modalities text[] NOT NULL DEFAULT '{}',
  tasks text[] NOT NULL DEFAULT '{}',
  search_text text NOT NULL DEFAULT '',
  search_vector tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(search_text, '')), 'B')
  ) STORED,
  embedding vector(384),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS datasets_search_vector_idx ON datasets USING gin(search_vector);
CREATE INDEX IF NOT EXISTS datasets_modalities_idx ON datasets USING gin(modalities);
CREATE INDEX IF NOT EXISTS datasets_tasks_idx ON datasets USING gin(tasks);
CREATE INDEX IF NOT EXISTS datasets_embedding_idx
  ON datasets USING hnsw (embedding vector_cosine_ops);

-- Legacy literature-search tables are retained so existing local data remains usable.
CREATE TABLE IF NOT EXISTS papers (
  pmcid text PRIMARY KEY,
  title text,
  licence text,
  methods_text text
);

CREATE TABLE IF NOT EXISTS extractions (
  pmcid text PRIMARY KEY REFERENCES papers(pmcid),
  species text,
  strain text,
  shock_intensity_ma text,
  n_pairings text,
  tone_duration_s text,
  apparatus text,
  sources jsonb,
  shock_values double precision[],
  n_pairings_int integer,
  tone_values double precision[],
  species_norm text,
  in_scope boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS chunks (
  id serial PRIMARY KEY,
  pmcid text REFERENCES papers(pmcid),
  chunk_index int,
  text text,
  embedding vector(384),
  UNIQUE (pmcid, chunk_index)
);
