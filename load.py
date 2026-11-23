"""Idempotently load normalized OpenNeuro metadata into PostgreSQL."""

import argparse

from database import initialize, load_json_records, upsert_dataset


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="datasets.json")
    args = parser.parse_args()
    datasets = load_json_records(args.input)
    initialize()
    for index, dataset in enumerate(datasets, 1):
        upsert_dataset(dataset)
        if index % 50 == 0:
            print(f"Loaded {index}/{len(datasets)} datasets")
    print(f"Loaded or updated {len(datasets)} datasets")


if __name__ == "__main__":
    main()
