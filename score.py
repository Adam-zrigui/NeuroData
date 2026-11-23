import csv
from collections import Counter

rows = list(csv.DictReader(open("labels.csv", encoding="utf-8-sig")))
c = Counter(r["label"].strip() for r in rows if r["label"].strip())
correct, wrong, missed = c["correct"], c["wrong"], c["missed"]
print(dict(c))
if correct + wrong:
    print("precision (returned values that are right):", round(correct / (correct + wrong), 2))
if correct + missed:
    print("recall (stated values that were found):", round(correct / (correct + missed), 2))