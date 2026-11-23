"""PostgreSQL access helpers for dataset indexing."""

import json
import os
import time
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb
from psycopg import OperationalError

load_dotenv()


def connect():
    database_url = os.getenv("DATABASE_URL")
    last_error = None
    for attempt in range(5):
        try:
            if database_url:
                conn = psycopg.connect(database_url, connect_timeout=8)
            else:
                conn = psycopg.connect(
                    host=os.getenv("DB_HOST", "localhost"),
                    port=int(os.getenv("DB_PORT", "5432")),
                    dbname=os.getenv("DB_NAME", "methodfinder"),
                    user=os.getenv("DB_USER", "postgres"),
                    password=os.getenv("DB_PASSWORD", "postgres"),
                    connect_timeout=8,
                )
            break
        except OperationalError as exc:
            last_error = exc
            if attempt == 4:
                raise
            time.sleep(0.5 * (2 ** attempt))
    if last_error and "conn" not in locals():
        raise last_error
    return conn


def initialize():
    sql = Path(__file__).with_name("init.sql").read_text(encoding="utf-8")
    with connect() as conn:
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(statement)


def upsert_dataset(dataset, embedding=None):
    fields = dataset["fields"]
    modalities = fields.get("modalities", {}).get("value") or []
    tasks = fields.get("tasks", {}).get("value") or []
    values = (
        dataset["dataset_id"], dataset["repository"], dataset["title"], dataset["url"],
        dataset.get("description", ""), dataset.get("licence"), dataset.get("doi"),
        Jsonb(fields), Jsonb(dataset.get("metadata", {})), modalities, tasks,
        dataset.get("description", ""), embedding,
    )
    sql = """
    INSERT INTO datasets (
      dataset_id, repository, title, url, description, licence, doi, fields, metadata,
      modalities, tasks, search_text, embedding
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    ON CONFLICT (dataset_id) DO UPDATE SET
      repository=EXCLUDED.repository, title=EXCLUDED.title, url=EXCLUDED.url,
      description=EXCLUDED.description, licence=EXCLUDED.licence, doi=EXCLUDED.doi,
      fields=EXCLUDED.fields, metadata=EXCLUDED.metadata, modalities=EXCLUDED.modalities,
      tasks=EXCLUDED.tasks, search_text=EXCLUDED.search_text,
      embedding=coalesce(EXCLUDED.embedding, datasets.embedding), updated_at=now()
    """
    with connect() as conn:
        conn.execute(sql, values)


def load_json_records(path="datasets.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    initialize()
    print("Database schema is ready.")
