import csv, json, re, sys
from textutil import squash

PAPERS = sys.argv[1:] or ["PMC13198912", "PMC13602953", "PMC13626168",
                          "PMC10165993", "PMC13489889"]
FIELDS = ["species", "strain", "shock_intensity_ma", "n_pairings",
          "tone_duration_s", "apparatus"]
HINTS = {
    "species": r"\b(mice|mouse|rats?)\b",
    "strain": r"c57|wistar|sprague|long[- ]?evans|balb|fischer",
    "shock_intensity_ma": r"\bma\b|milliamp|footshock|foot shock",
    "n_pairings": r"pairing|trials?\b|presentations?",
    "tone_duration_s": r"\btone|\bcue\b|\bcs\b",
    "apparatus": r"chamber|box|apparatus|cage",
}

clean = json.load(open("clean_extractions.json", encoding="utf-8"))
papers = {p["pmcid"]: p for p in json.load(open("papers.json", encoding="utf-8"))}

with open("labels.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["pmcid", "field", "value", "quote", "label", "paper_sentences"])
    for pmcid in PAPERS:
        sentences = re.split(r"(?<=[.!?])\s+", squash(papers[pmcid]["methods_text"]))
        for field in FIELDS:
            f = clean[pmcid][field]
            hits = [s for s in sentences if re.search(HINTS[field], s, re.I)][:3]
            w.writerow([pmcid, field, f["value"], f["source"], "",
                        " || ".join(h[:200] for h in hits)])
print("wrote labels.csv")