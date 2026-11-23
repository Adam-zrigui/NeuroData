import glob, json
import os
from textutil import verify
import glob, json
NULLISH = {"null", "none", "n/a", "not stated", ""}


def denull(fields):
    for f in fields.values():
        for k in ("value", "source"):
            if isinstance(f[k], str) and f[k].strip().lower() in NULLISH:
                f[k] = None
    return fields
for path in glob.glob("extractions*.json"):
    d = json.load(open(path, encoding="utf-8"))
    if "PMC13717115" in d:
        print(path, d["PMC13717115"]["species"], d["PMC13717115"]["strain"])
cues = json.load(open("cue_types.json", encoding="utf-8")) if os.path.exists("cue_types.json") else {}

records = {r["pmcid"]: r for r in json.load(open("papers.json", encoding="utf-8"))}
clean = {}
for path in sorted(glob.glob("extractions*.json")):
    for pmcid, fields in json.load(open(path, encoding="utf-8")).items():
        if cues.get(pmcid, {}).get("cue_type") == "none":
          fields["n_pairings"] = {"value": None, "source": None}
          fields["tone_duration_s"] = {"value": None, "source": None}
        clean[pmcid] =verify(denull(fields), records[pmcid]["methods_text"], label=pmcid)
json.dump(clean, open("clean_extractions.json", "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)
print(len(clean), "papers")