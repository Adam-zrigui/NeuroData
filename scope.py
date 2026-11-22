import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
conn = psycopg.connect(host="localhost", dbname="methodfinder",
                       user="postgres", password=os.getenv("DB_PASSWORD"))
with conn.cursor() as cur:
    cur.execute("""SELECT e.pmcid, e.species_norm, e.species, e.strain, left(p.title, 70)
                   FROM extractions e JOIN papers p USING (pmcid)
                   WHERE e.species_norm IS NULL OR e.species_norm = 'other'
                   ORDER BY e.species_norm NULLS LAST""")
    for row in cur.fetchall():
        print(row)