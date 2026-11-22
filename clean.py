import glob, json
import os
from textutil import verify
cues = json.load(open("cue_types.json", encoding="utf-8")) if os.path.exists("cue_types.json") else {}

records = {r["pmcid"]: r for r in json.load(open("papers.json", encoding="utf-8"))}
clean = {}
for path in sorted(glob.glob("extractions*.json")):
    for pmcid, fields in json.load(open(path, encoding="utf-8")).items():
        if cues.get(pmcid, {}).get("cue_type") == "none":
          fields["n_pairings"] = {"value": None, "source": None}
          fields["tone_duration_s"] = {"value": None, "source": None}
        clean[pmcid] = verify(fields, records[pmcid]["methods_text"])
json.dump(clean, open("clean_extractions.json", "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)
print(len(clean), "papers")