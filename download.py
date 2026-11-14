import requests, pathlib, time

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
out = pathlib.Path("papers"); out.mkdir(exist_ok=True)


r = requests.get(f"{BASE}/search", params={
    "query": 'TITLE:"fear conditioning"  AND OPEN_ACCESS:y AND SRC:MED AND (ABSTRACT:"mouse" OR ABSTRACT:"mice" OR ABSTRACT:"rat" OR ABSTRACT:"rats")',
    "format": "json", "pageSize": 1000, "resultType": "lite",
})
r.raise_for_status()
data = r.json()
print(f"Found {data['hitCount']} papers matching the query")
for p in data["resultList"]["result"]:
    pmcid = p.get("pmcid")
 
    if not pmcid:
         print(f"Skipping {p.get('title')} because it has no PMCID")
         continue
    if (out / f"{pmcid}.xml").exists():
        continue
    x = requests.get(f"{BASE}/{pmcid}/fullTextXML")
    
    if x.ok:
        print(f"Downloaded {p.get('title')}")
        (out / f"{pmcid}.xml").write_text(x.text, encoding="utf-8")
    else:
        print(f"Failed to download {pmcid}: {x.status_code}")

    time.sleep(0.5) 