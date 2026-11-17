import json, os
import psycopg
from psycopg.types.json import Jsonb
from dotenv import load_dotenv
load_dotenv()
conn = psycopg.connect(
    host="localhost", dbname="methodfinder", user="postgres", password=os.getenv("DB_PASSWORD")
)
papers = json.load(open("papers.json", encoding="utf-8"))
extractions = json.load(open("extractions.json", encoding="utf-8")) if os.path.exists("extractions.json") else {}
FIELDS = ["species", "strain", "shock_intensity_ma", "n_pairings", "tone_duration_s", "apparatus"]
cols =", ".join(FIELDS)
marks = ", ".join(["%s"] * (len(FIELDS) + 2))  # +2 for pmcid and sources
updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in FIELDS + ["sources"])
with conn, conn.cursor() as cur:
    for p in papers:
        cur.execute(
                    """INSERT INTO papers (pmcid, title, licence, methods_text)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (pmcid) DO UPDATE SET
                 title = EXCLUDED.title, licence = EXCLUDED.licence,
                 methods_text = EXCLUDED.methods_text""",
            (p["pmcid"], p["title"], p["licence"], p["methods_text"]),
        )
    for pmcid, f in extractions.items():
        values = [f[k]["value"] for k in FIELDS]
        sources = {k: f[k]["source"] for k in FIELDS}
        cur.execute(
            f"""INSERT INTO extractions (pmcid, {cols}, sources)
                VALUES ({marks})
                ON CONFLICT (pmcid) DO UPDATE SET {updates}""",
            (pmcid, *values, Jsonb(sources)),
        )
print("loaded", len(papers), "papers and", len(extractions), "extractions")