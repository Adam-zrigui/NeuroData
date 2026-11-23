"""Evaluate retrieval on human-judged requests supplied as eval_set.json.

Expected JSON: [{"query": "...", "relevant_dataset_ids": ["ds000001", ...]}]
Do not populate this file with guessed relevance labels.
"""

import argparse
import json
from pathlib import Path

from parse_query import parse_query
from search_core import search


def metrics(ranked, relevant, k=10):
    top = ranked[:k]
    precision = sum(dataset_id in relevant for dataset_id in top) / k
    recall = sum(dataset_id in relevant for dataset_id in top) / len(relevant) if relevant else 0.0
    first = next((index for index, dataset_id in enumerate(ranked, 1) if dataset_id in relevant), None)
    return precision, recall, 1 / first if first else 0.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("eval_set.json"))
    args = parser.parse_args()
    cases = json.loads(args.input.read_text(encoding="utf-8"))
    if not cases:
        raise SystemExit("Evaluation set is empty.")
    totals = {mode: [0.0, 0.0, 0.0] for mode in ("filters", "keyword", "vector", "hybrid")}
    for case in cases:
        parsed = parse_query(case["query"])
        relevant = set(case.get("relevant_dataset_ids", []))
        for mode in totals:
            results = search(case["query"], parsed.filters, 10, mode)
            ranked = [item["dataset"]["dataset_id"] for item in results]
            values = metrics(ranked, relevant)
            totals[mode] = [a + b for a, b in zip(totals[mode], values)]
    print(f"Evaluated {len(cases)} judged requests")
    print("mode       P@10   R@10   MRR")
    for mode, (precision, recall, mrr) in totals.items():
        n = len(cases)
        print(f"{mode:<10} {precision/n:.3f}  {recall/n:.3f}  {mrr/n:.3f}")


if __name__ == "__main__":
    main()
