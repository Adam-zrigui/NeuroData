"""Optional, evidence-constrained extraction of fields from cached metadata text.

Structured OpenNeuro fields are populated first by dataset_schema.normalize(). This step only
asks a model about missing fields and accepts an answer only when its source is an exact quote.
"""

import json
import os
import argparse
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

INPUT = Path("datasets.json")
OUTPUT = Path("datasets.json")
FIELDS = ("population", "longitudinal", "resting_state", "processed_data_available",
          "field_strength", "paper_doi", "age_min", "age_max")


def extract(text, missing):
    client = OpenAI(
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=os.environ["OPENROUTER_API_KEY"], timeout=60, max_retries=2,
    )
    properties = {}
    for key in missing:
        properties[key] = {
            "type": "object",
            "properties": {
                "value": {"type": ["string", "number", "boolean", "null"]},
                "source": {"type": ["string", "null"]},
            },
            "required": ["value", "source"],
            "additionalProperties": False,
        }
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "google/gemma-4-26b-a4b-it:free"),
        messages=[
            {"role": "system", "content": (
                "Extract dataset facts only when explicitly stated in the supplied metadata. "
                "Do not infer, calculate, or guess. Return null for absent information. "
                "A source must be copied exactly from the supplied text. Ages are in years."
            )},
            {"role": "user", "content": "Fields: " + ", ".join(missing) + "\nTEXT:\n" + text[:18000]},
        ],
        response_format={"type": "json_schema", "json_schema": {
            "name": "dataset_metadata", "strict": True,
            "schema": {"type": "object", "properties": properties,
                       "required": list(properties), "additionalProperties": False},
        }},
    )
    return json.loads(response.choices[0].message.content or "{}")


def main():
    parser = argparse.ArgumentParser(description="Fill missing dataset metadata conservatively.")
    parser.add_argument("--limit", type=int, default=int(os.getenv("LLM_EXTRACTION_LIMIT", "20")),
                        help="Maximum number of model calls this run (default: 20).")
    args = parser.parse_args()
    if not INPUT.exists():
        raise SystemExit("datasets.json is missing. Run `python parse.py` first.")
    datasets = json.loads(INPUT.read_text(encoding="utf-8"))
    if not os.getenv("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY is not configured; unresolved fields will stay not stated.")
        return
    progress_path = Path("extract_progress.json")
    processed_ids = set(json.loads(progress_path.read_text(encoding="utf-8"))) if progress_path.exists() else set()
    calls = 0
    for index, dataset in enumerate(datasets, 1):
        # Current GraphQL fields can include text metadata; future API fields can add README text here.
        text = dataset.get("metadata_text") or dataset.get("description", "")
        missing = [key for key in FIELDS if dataset["fields"].get(key, {}).get("status") == "not_stated"]
        if dataset["dataset_id"] in processed_ids or not text.strip() or not missing:
            continue
        if calls >= max(0, args.limit):
            break
        calls += 1
        try:
            result = extract(text, missing)
        except Exception as exc:
            print(f"Extraction failed for {dataset['dataset_id']}: {str(exc)[:120]}")
            continue
        for key in missing:
            field = result.get(key) or {}
            value, quote = field.get("value"), field.get("source")
            if value is None or not quote or quote not in text:
                continue
            dataset["fields"][key] = {"value": value, "status": "stated", "source": quote}
        processed_ids.add(dataset["dataset_id"])
        progress_path.write_text(json.dumps(sorted(processed_ids), indent=2), encoding="utf-8")
        OUTPUT.write_text(json.dumps(datasets, ensure_ascii=False, indent=2), encoding="utf-8")
        if index % 10 == 0:
            print(f"Processed {index}/{len(datasets)} datasets")
        time.sleep(float(os.getenv("LLM_REQUEST_DELAY", "1")))
    OUTPUT.write_text(json.dumps(datasets, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved evidence-checked metadata to {OUTPUT}")
    print(f"Used {calls} model calls this run; run again to continue from saved progress.")


if __name__ == "__main__":
    main()
