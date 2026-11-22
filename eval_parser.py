import json, time
from parse_query import parse_rules, parse_query

FIELDS = ["species", "shock_ma", "n_pairings", "tone_duration_s"]
cases = json.load(open("parser_tests.json", encoding="utf-8"))
parsers = {"rules": parse_rules, "llm": parse_query}
hits = {p: dict.fromkeys(FIELDS, 0) for p in parsers}
errors = {p: 0 for p in parsers}

for c in cases:
    exp = {f: c["expected"].get(f) for f in FIELDS}
    for name, fn in parsers.items():
        if name == "llm":
            time.sleep(6)                     # stay under the free-tier limits
        try:
            got = fn(c["text"]).model_dump()
        except Exception:
            errors[name] += 1
            continue
        for f in FIELDS:
            if got[f] == exp[f]:
                hits[name][f] += 1
            else:
                print(f"MISS [{name}] {c['text']!r} {f}: expected {exp[f]}, got {got[f]}")

n = len(cases)
for name in parsers:
    print(name, {f: f"{hits[name][f]}/{n - errors[name]}" for f in FIELDS}, "errors:", errors[name])