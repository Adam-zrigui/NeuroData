"""Hybrid keyword/vector retrieval and evidence-based requirement explanations."""

import os

from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

import database

load_dotenv()


def _embedding(text):
    model = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    return model.encode(text, normalize_embeddings=True).tolist()


def _value(fields, name):
    return (fields.get(name) or {}).get("value")


def _source(fields, name):
    return (fields.get(name) or {}).get("source")


def explain(fields, filters):
    checks = []
    for name, expected in filters.model_dump().items():
        if expected is None or expected == []:
            continue
        field_name = "n_participants" if name == "min_participants" else name
        actual = _value(fields, field_name)
        status = "not_stated"
        if actual is not None:
            if name == "modalities":
                actual_values = {str(x).lower() for x in (actual if isinstance(actual, list) else [actual])}
                desired = {x.lower() for x in expected}
                if "fmri" in desired and "mri" in actual_values and not actual_values.intersection({"fmri", "bold"}):
                    status = "not_stated"
                else:
                    status = "met" if actual_values.intersection(desired) else "not_met"
            elif name == "tasks":
                actual_text = " ".join(actual if isinstance(actual, list) else [str(actual)]).lower()
                status = "met" if all(str(x).lower() in actual_text for x in expected) else "not_met"
            elif name == "min_participants":
                status = "met" if actual >= expected else "not_met"
            elif name == "min_age":
                maximum = _value(fields, "age_max")
                minimum = _value(fields, "age_min")
                if minimum is not None and minimum >= expected:
                    status = "met"
                elif maximum is not None and maximum < expected:
                    status = "not_met"
            elif name == "max_age":
                maximum = _value(fields, "age_max")
                minimum = _value(fields, "age_min")
                if maximum is not None and maximum <= expected:
                    status = "met"
                elif minimum is not None and minimum > expected:
                    status = "not_met"
            elif isinstance(expected, bool):
                status = "met" if actual is expected else "not_met"
            else:
                status = "met" if str(actual).lower() == str(expected).lower() else "not_met"
        checks.append({
            "requirement": f"{name.replace('_', ' ')}: {expected}",
            "status": status,
            "value": actual,
            "source": _source(fields, field_name),
        })
    return checks


def search(query, filters, limit=10, mode="hybrid"):
    if mode not in {"filters", "keyword", "vector", "hybrid"}:
        raise ValueError("mode must be filters, keyword, vector, or hybrid")
    query_vector = None
    if mode in {"vector", "hybrid"}:
        try:
            query_vector = _embedding(query)
        except Exception as exc:
            if mode == "vector":
                raise RuntimeError(f"Embedding model unavailable: {exc}") from exc
            print(f"Embedding model unavailable; using keyword ranking only ({exc})")

    with database.connect() as conn:
        register_vector(conn)
        if mode == "filters":
            rows = conn.execute("""
                SELECT dataset_id, repository, title, url, description, licence, doi, fields, metadata,
                       0::double precision AS lexical_score, NULL::double precision AS vector_distance
                FROM datasets ORDER BY title
            """).fetchall()
        elif query_vector is None:
            rows = conn.execute("""
                SELECT dataset_id, repository, title, url, description, licence, doi, fields, metadata,
                       ts_rank_cd(search_vector, websearch_to_tsquery('english', %s)) AS lexical_score,
                       NULL::double precision AS vector_distance
                FROM datasets
                ORDER BY lexical_score DESC, title
                LIMIT 500
            """, (query,)).fetchall()
        elif mode == "vector":
            rows = conn.execute("""
                SELECT dataset_id, repository, title, url, description, licence, doi, fields, metadata,
                       0::double precision AS lexical_score, embedding <=> %s AS vector_distance
                FROM datasets WHERE embedding IS NOT NULL
                ORDER BY vector_distance LIMIT 500
            """, (query_vector,)).fetchall()
        else:
            rows = conn.execute("""
                WITH candidates AS (
                  SELECT dataset_id, repository, title, url, description, licence, doi, fields, metadata,
                    CASE WHEN search_vector @@ websearch_to_tsquery('english', %s)
                         THEN ts_rank_cd(search_vector, websearch_to_tsquery('english', %s)) ELSE 0 END AS lexical_score,
                    CASE WHEN embedding IS NULL THEN NULL ELSE embedding <=> %s END AS vector_distance
                  FROM datasets
                ), ranks AS (
                  SELECT *,
                    row_number() OVER (ORDER BY lexical_score DESC, dataset_id) AS lexical_rank,
                    row_number() OVER (ORDER BY vector_distance ASC NULLS LAST, dataset_id) AS vector_rank
                  FROM candidates
                )
                SELECT dataset_id, repository, title, url, description, licence, doi, fields, metadata,
                       lexical_score, vector_distance,
                       (1.0 / (60 + lexical_rank) +
                        CASE WHEN vector_distance IS NULL THEN 0 ELSE 1.0 / (60 + vector_rank) END) AS rrf
                FROM ranks
                ORDER BY rrf DESC
                LIMIT 500
            """, (query, query, query_vector)).fetchall()

    results = []
    for row in rows:
        dataset_id, repository, title, url, description, licence, doi, fields, metadata = row[:9]
        lexical = float(row[9] or 0)
        rrf = float(row[11] if len(row) > 11 and row[11] is not None else lexical)
        explanations = explain(fields or {}, filters)
        met = sum(item["status"] == "met" for item in explanations)
        not_met = sum(item["status"] == "not_met" for item in explanations)
        if mode == "filters":
            final_score = met - not_met * 0.25
        elif mode == "keyword":
            final_score = lexical
        elif mode == "vector":
            distance = row[10]
            final_score = 1.0 / (1.0 + float(distance or 1.0))
        else:
            final_score = rrf + met * 0.001 - not_met * 0.002
        results.append({
            "dataset": {
                "dataset_id": dataset_id, "repository": repository, "title": title,
                "url": url, "description": description, "licence": licence,
                "doi": doi, "fields": fields or {}, "metadata": metadata or {},
            },
            "score": final_score,
            "explanations": explanations,
        })
    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:limit]
