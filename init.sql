CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE papers (
  pmcid text PRIMARY KEY,
  title text,
  licence text,
  methods_text text
);

CREATE TABLE extractions (
  pmcid text PRIMARY KEY REFERENCES papers(pmcid),
  species text,
  strain text,
  shock_intensity_ma text,
  n_pairings text,
  tone_duration_s text,
  apparatus text,
  sources jsonb
);

CREATE TABLE chunks (
  id serial PRIMARY KEY,
  pmcid text REFERENCES papers(pmcid),
  chunk_index int,
  text text,
  embedding vector(384)
);