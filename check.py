import json

def squash(s):
    return " ".join(s.split())

records = {r["pmcid"]: r for r in json.load(open("papers.json", encoding="utf-8"))}
out = json.load(open("extractions.json", encoding="utf-8"))

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

print("found", found, "not found", missing, "null", nulls)