import os, re, sys
import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from normalise import to_int
load_dotenv()
conn = psycopg.connect(
    host="localhost", dbname="methodfinder", user="postgres", password=os.getenv("DB_PASSWORD"))
register_vector(conn)
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
query = sys.argv[1]
qvec = model.encode(query)
filters = []
params = [qvec]

shock_match = re.search(r"\b(\d+(?:\.\d+)?)\s*mA\b", query, re.IGNORECASE)
if shock_match:
    filters.append("%s = ANY(e.shock_values)")
    params.append(float(shock_match.group(1)))

pairings_match = re.search(
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)"
    r"\s+(?:tone[- ]shock\s+)?pairings?\b",
    query,
    re.IGNORECASE,
)
if pairings_match:
    filters.append("e.n_pairings_int = %s")
    params.append(to_int(pairings_match.group(1)))
seen = set()
where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
with conn, conn.cursor() as cur:
    cur.execute(
        f"""SELECT c.pmcid, e.species, e.shock_intensity_ma,
                  c.embedding <=> %s AS dist, left(c.text, 150)
           FROM chunks c JOIN extractions e USING (pmcid)
          {where_clause}
          ORDER BY dist LIMIT 5""",
        params,
    )
    for row in cur.fetchall():
        if row[0] in seen:
            continue
        seen.add(row[0])
        print(row)