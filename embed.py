"""Create local 384-dimensional embeddings for dataset metadata."""

import os

from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

import database

load_dotenv()


def main():
    model = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    with database.connect() as conn:
        register_vector(conn)
        rows = conn.execute(
            "SELECT dataset_id, concat_ws(E'\\n', title, search_text) FROM datasets "
            "WHERE embedding IS NULL ORDER BY dataset_id"
        ).fetchall()
    batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        vectors = model.encode([text for _, text in batch], normalize_embeddings=True)
        with database.connect() as conn:
            conn.executemany(
                "UPDATE datasets SET embedding=%s, updated_at=now() WHERE dataset_id=%s",
                [(vector.tolist(), dataset_id) for (dataset_id, _), vector in zip(batch, vectors)],
            )
        print(f"Embedded {min(start + len(batch), len(rows))}/{len(rows)} datasets")
    print("Embedding pass complete")


if __name__ == "__main__":
    main()
