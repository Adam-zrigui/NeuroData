"""Cache public OpenNeuro dataset metadata through its GraphQL API.

This script requests metadata only. It never downloads dataset data files.
"""

import hashlib
import json
import math
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()

ENDPOINT = os.getenv("OPENNEURO_ENDPOINT", "https://openneuro.org/crn/graphql")
CACHE = Path(os.getenv("OPENNEURO_CACHE_DIR", ".cache/openneuro"))
DELAY = float(os.getenv("OPENNEURO_REQUEST_DELAY", "0.5"))
PAGE_SIZE = int(os.getenv("OPENNEURO_PAGE_SIZE", "50"))
LIMIT = int(os.getenv("OPENNEURO_LIMIT", "0")) or None

QUERY = """
query PublicDatasets($count: Int!, $after: String) {
  datasets(first: $count, after: $after, orderBy: {created: ascending},
           filterBy: {public: true}) {
    edges { node {
      id name created publishDate
      latestSnapshot {
        tag
        created
        size
        dataset {
          name
          metadata {
            trialCount studyDesign studyDomain studyLongitudinal dataProcessed species
            associatedPaperDOI openneuroPaperDOI dxStatus
          }
        }
        description {
          Name BIDSVersion DatasetDOI License Authors Acknowledgements
          HowToAcknowledge Funding ReferencesAndLinks SeniorAuthor DatasetType
        }
        summary {
          modalities secondaryModalities tasks subjects dataProcessed
          subjectMetadata { age }
        }
      }
    } }
    pageInfo { endCursor hasNextPage count }
  }
}
"""


def fetch_page(session, cursor, count):
    cursor_key = cursor or "first"
    digest = hashlib.sha256(f"{ENDPOINT}:{QUERY}:{cursor_key}:{count}".encode()).hexdigest()[:16]
    path = CACHE / f"page-{digest}.json"
    if path.exists() and os.getenv("OPENNEURO_REFRESH", "0") != "1":
        return json.loads(path.read_text(encoding="utf-8"))

    response = session.post(
        ENDPOINT,
        json={"query": QUERY, "variables": {"count": count, "after": cursor}},
        timeout=(10, 60),
    )
    response.raise_for_status()
    body = response.json()
    if body.get("errors"):
        raise RuntimeError(f"OpenNeuro GraphQL returned errors: {body['errors']}")
    # Reduce participant-level ages to a cohort range and discard row-level values immediately.
    for edge in body.get("data", {}).get("datasets", {}).get("edges", []):
        summary = (((edge or {}).get("node") or {}).get("latestSnapshot") or {}).get("summary") or {}
        subject_ids = summary.pop("subjects", None)
        summary["subjectCount"] = len(subject_ids) if isinstance(subject_ids, list) else subject_ids
        ages = []
        for subject in summary.pop("subjectMetadata", []) or []:
            try:
                age = float(subject.get("age")) if isinstance(subject, dict) else None
                if age is not None and math.isfinite(age):
                    ages.append(age)
            except (TypeError, ValueError):
                continue
        summary["ageRange"] = {"min": min(ages), "max": max(ages)} if ages else None
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    if DELAY > 0:
        time.sleep(DELAY)
    return body


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    retry = Retry(
        total=4, connect=4, read=4, backoff_factor=0.7,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"POST"}),
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "NeuroDataFinder/0.1 (public metadata indexer)"})
    records, cursor, page = [], None, 0
    while LIMIT is None or len(records) < LIMIT:
        count = PAGE_SIZE if LIMIT is None else min(PAGE_SIZE, LIMIT - len(records))
        body = fetch_page(session, cursor, count)
        connection = body.get("data", {}).get("datasets")
        if not connection:
            raise RuntimeError("OpenNeuro response has no public datasets connection")
        records.extend(edge["node"] for edge in connection.get("edges", []) if edge.get("node"))
        info = connection.get("pageInfo") or {}
        print(f"Fetched page {page + 1}: {len(records)} public datasets so far")
        if not info.get("hasNextPage") or not info.get("endCursor"):
            break
        cursor, page = info["endCursor"], page + 1

    output = Path("openneuro_raw.json")
    output.write_text(json.dumps(records[:LIMIT], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Cached {min(len(records), LIMIT) if LIMIT else len(records)} dataset records in {output}")


if __name__ == "__main__":
    main()
