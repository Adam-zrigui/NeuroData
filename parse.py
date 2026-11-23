"""Normalize cached OpenNeuro metadata into the v1 dataset schema."""

import json
from pathlib import Path

from dataset_schema import is_mri_dataset, normalize

SOURCE = Path("openneuro_raw.json")
OUTPUT = Path("datasets.json")


def main():
    if not SOURCE.exists():
        raise SystemExit("openneuro_raw.json is missing. Run `python download.py` first.")
    raw = json.loads(SOURCE.read_text(encoding="utf-8"))
    datasets = [normalize(record) for record in raw]
    mri_datasets = [record for record in datasets if is_mri_dataset(record)]
    OUTPUT.write_text(json.dumps(mri_datasets, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Normalized {len(mri_datasets)} MRI/fMRI datasets from {len(datasets)} public records")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
