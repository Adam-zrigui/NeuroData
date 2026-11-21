import json
import sys
from extract import extract_patiently
from textutil import squash
from textutil import verify
out = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "extractions.json", encoding="utf-8"))



records = {r["pmcid"]: r for r in json.load(open("papers.json", encoding="utf-8"))}

found = missing = nulls = 0
for pmcid, fields in out.items():
    text = squash(records[pmcid]["methods_text"])
    for name, f in fields.items():
        if f["value"] is None:
            nulls += 1
        elif f["source"] and squash(f["source"]) in text:
            found += 1
        else:
            missing += 1
            print("NOT FOUND:", pmcid, name, "|", f["source"])
out[records[pmcid]["pmcid"]] = verify(extract_patiently(records[pmcid]["methods_text"]), records[pmcid]["methods_text"])
print("found", found, "not found", missing, "null", nulls)