import argparse, os, sys
import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer
from parse_query import parse

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

ap = argparse.ArgumentParser()
ap.add_argument("query")
ap.add_argument("--species", choices=["mouse", "rat"])
ap.add_argument("--shock", type=float)
ap.add_argument("--pairings", type=int)
ap.add_argument("--tone", type=float)
ap.add_argument("--limit", type=int, default=10)
ap.add_argument("--no-parse", action="store_true", help="skip the LLM, use flags only")
a = ap.parse_args()

filters = {"species": None, "shock_ma": None, "n_pairings": None, "tone_duration_s": None}
if not a.no_parse:
    try:
        filters.update(parse(a.query).model_dump())
    except Exception as e:
        print("could not parse the request, using flags only:", str(e)[:150])

# command-line flags override whatever the LLM returned
if a.species:
    filters["species"] = a.species
if a.shock is not None:
    filters["shock_ma"] = a.shock
if a.pairings is not None:
    filters["n_pairings"] = a.pairings
if a.tone is not None:
    filters["tone_duration_s"] = a.tone

print("filters:", {k: v for k, v in filters.items() if v is not None} or "none")

conds, params = ["e.in_scope"], []
if filters["species"]:
    conds.append("e.species_norm IN (%s, 'both')");  params.append(filters["species"])
if filters["shock_ma"] is not None:
    conds.append("%s = ANY(e.shock_values)");        params.append(filters["shock_ma"])
if filters["n_pairings"] is not None:
    conds.append("e.n_pairings_int = %s");           params.append(filters["n_pairings"])
if filters["tone_duration_s"] is not None:
    conds.append("%s = ANY(e.tone_values)");         params.append(filters["tone_duration_s"])
where = " AND ".join(conds)

conn = psycopg.connect(host="localhost", dbname="methodfinder",
                       user="postgres", password=os.getenv("DB_PASSWORD"))
register_vector(conn)
model = SentenceTransformer("all-MiniLM-L6-v2")
qvec = model.encode(a.query)

sql = f"""
SELECT * FROM (
  SELECT DISTINCT ON (c.pmcid)
         c.pmcid, p.title, p.licence, e.species_norm,
         e.shock_intensity_ma, e.n_pairings, e.tone_duration_s, e.sources,
         c.embedding <=> %s AS dist
  FROM chunks c
  JOIN extractions e USING (pmcid)
  JOIN papers p USING (pmcid)
  WHERE {where}
  ORDER BY c.pmcid, dist
) t ORDER BY dist LIMIT %s
"""

with conn.cursor() as cur:
    cur.execute(sql, (qvec, *params, a.limit))
    rows = cur.fetchall()

print(f"{len(rows)} papers\n")
for pmcid, title, licence, sp, shock, npair, tone, sources, dist in rows:
    print(f"{pmcid}  {title[:80]}")
    print(f"  {sp} | shock {shock} | pairings {npair} | tone {tone} | {licence}")
    for key in ("shock_intensity_ma", "n_pairings"):
        quote = sources.get(key)
        if quote:
            print(f'  {key}: "{quote[:200]}"')
    print(f"  https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/\n")