"""Search the indexed OpenNeuro MRI/fMRI dataset metadata."""

import argparse
import json

from parse_query import Filters, parse_query
from search_core import search


def main():
    parser = argparse.ArgumentParser(description="Find public neuroscience datasets from a plain-language request.")
    parser.add_argument("query", help="Describe the dataset you need")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--filters", help="Path to a JSON file of editable filters")
    parser.add_argument("--no-parse", action="store_true", help="Use only the request's semantic text")
    parser.add_argument("--mode", choices=("filters", "keyword", "vector", "hybrid"), default="hybrid")
    args = parser.parse_args()

    parsed = parse_query(args.query)
    if args.no_parse:
        parsed.filters = Filters()
    if args.filters:
        parsed.filters = Filters.model_validate_json(open(args.filters, encoding="utf-8").read())
    print("Parsed filters (edit with --filters <json>):")
    print(json.dumps(parsed.filters.model_dump(), indent=2, ensure_ascii=False))
    results = search(parsed.semantic_query, parsed.filters, max(1, min(args.limit, 50)), args.mode)
    if not results:
        print("No indexed datasets. Run the harvest, load, and embed steps first.")
        return
    for result in results:
        item = result["dataset"]
        print(f"\n{item['dataset_id']}  {item['title']}\n  {item['url']}  score={result['score']:.4f}")
        print(f"  Licence: {item['licence'] or 'not stated'}")
        for explanation in result["explanations"]:
            print(f"  {explanation['status']}: {explanation['requirement']} — {explanation['value']!r}")
            if explanation["source"]:
                print(f"    Evidence: {explanation['source']}")
    print("\nMatches are suggestions. Review the source dataset page and documentation before use.")


if __name__ == "__main__":
    main()
