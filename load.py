import json, os
import psycopg
from psycopg.types.json import Jsonb
from dotenv import load_dotenv
from normalise import numbers, to_int, species_norm

load_dotenv()
conn = psycopg.connect(
    host="localhost", dbname="methodfinder",
    user="postgres", password=os.getenv("DB_PASSWORD"),
)

papers = json.load(open("papers.json", encoding="utf-8"))
extractions = json.load(open("clean_extractions.json", encoding="utf-8"))

FIELDS = ["species", "strain", "shock_intensity_ma",
          "n_pairings", "tone_duration_s", "apparatus"]
COLUMNS = FIELDS + ["shock_values", "tone_values", "n_pairings_int", "species_norm",
                    "in_scope", "sources"]

marks = ", ".join(["%s"] * (len(COLUMNS) + 1))      # +1 for pmcid
col_list = ", ".join(COLUMNS)
updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in COLUMNS)

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
        sn = species_norm(f["species"]["value"], f["strain"]["value"])
        values = [f[k]["value"] for k in FIELDS]
        values += [
            numbers(f["shock_intensity_ma"]["value"]),
            numbers(f["tone_duration_s"]["value"]),
            to_int(f["n_pairings"]["value"]),
            sn,
            sn in ("mouse", "rat", "both"),
            Jsonb({k: f[k]["source"] for k in FIELDS}),
        ]
        cur.execute(
            f"""INSERT INTO extractions (pmcid, {col_list})
                VALUES ({marks})
                ON CONFLICT (pmcid) DO UPDATE SET {updates}""",
            (pmcid, *values),
        )

print("loaded", len(papers), "papers and", len(extractions), "extractions")