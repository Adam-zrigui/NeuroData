import requests, pathlib, time

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
out = pathlib.Path("papers"); out.mkdir(exist_ok=True)

r = requests.get(f"{BASE}/search", params={
    "query": 'TITLE:"fear conditioning"  AND OPEN_ACCESS:y AND SRC:MED AND ("mouse" OR "mice" OR "rat" OR "rats")',
    "format": "json", "pageSize": 50, "resultType": "lite",
})
r.raise_for_status()

for p in r.json()["resultList"]["result"]:
    pmcid = p.get("pmcid")
  
    if not pmcid:
         print(f"Skipping {p.get('title')} because it has no PMCID")
         continue
    x = requests.get(f"{BASE}/{pmcid}/fullTextXML")
    
    if x.ok:
        print(f"Downloaded {p.get('title')}")
        (out / f"{pmcid}.xml").write_text(x.text, encoding="utf-8")
    else:
        print(f"Failed to download {pmcid}: {x.status_code}")

    time.sleep(0.5)  # keep the request rate low