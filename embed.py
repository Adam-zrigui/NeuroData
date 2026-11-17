import os
import psycopg
from pgvector.psycopg import register_vector
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
load_dotenv()
conn = psycopg.connect(
    host="localhost", dbname="methodfinder", user="postgres", password=os.getenv("DB_PASSWORD"))
register_vector(conn)
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
def chunk(text, size=120, overlap=20):
    words = text.split()
    step = size - overlap
    return [" ".join(words[i:i + size]) for i in range(0, len(words), step)]
with conn, conn.cursor() as cur:
    cur.execute("SELECT pmcid, methods_text FROM papers")
    for pmcid, text in cur.fetchall(): 
     pieces = chunk(text)
     vectors = model.encode(pieces)
     for i, (piece, vector) in enumerate(zip(pieces, vectors)):
         cur.execute(
                "INSERT INTO chunks (pmcid, chunk_index, text, embedding) VALUES (%s, %s, %s, %s)",
             (pmcid, i, piece, vector)
         )
print("done")
         