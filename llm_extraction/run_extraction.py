"""
run_extraction.py — OTF-04 LLM extraction prototype

Orchestrates the full pipeline for the two seed articles:

  1. Ensure every manifest article is cached locally (fetch_articles.py).
  2. Call extract_openai.py once per article.
  3. Run every record's verbatim_quote (and, when non-null,
     approx_participants) through grounding_check.py.
  4. Stamp grounding_checker_version and review_status.
  5. Write output/otf04_extractions.jsonl and .csv *before* touching
     BigQuery, so a BQ load failure never forces re-billing the LLM call.
  6. Append-load into llm_derived.article_extractions (never
     create+replace -- this is a running log of extraction runs).
  7. Print a grounding summary.

Run manually only, never via `bruin run` -- see setup_bigquery.py's
docstring and ADR-0009 for why. Requires setup_bigquery.py to have been
run at least once first (creates the dataset/table this script loads
into).
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

import fetch_articles  # noqa: E402
from extract_openai import ExtractionError, extract_events_from_article  # noqa: E402
from grounding_check import CHECKER_VERSION, check_quote_grounding  # noqa: E402

MANIFEST_PATH = REPO_ROOT / "source_articles_manifest.json"
CACHE_DIR = REPO_ROOT / "source_articles_cache"
OUTPUT_DIR = REPO_ROOT / "output"
JSONL_PATH = OUTPUT_DIR / "otf04_extractions.jsonl"
CSV_PATH = OUTPUT_DIR / "otf04_extractions.csv"

CSV_COLUMNS = [
    "source_article_id",
    "event_date",
    "location_text",
    "approx_participants",
    "event_type",
    "description",
    "verbatim_quote",
    "grounding_status",
    "grounding_similarity",
    "participants_grounding_status",
    "llm_derived",
    "extraction_model",
    "extraction_timestamp_utc",
    "prompt_version_hash",
    "grounding_checker_version",
    "review_status",
]


def _load_body_text(article_id: str) -> str:
    path = CACHE_DIR / f"{article_id}.txt"
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return raw.split("===BODY===", 1)[1].strip()


def _ground_record(record: dict, source_text: str) -> dict:
    quote_result = check_quote_grounding(record["verbatim_quote"], source_text)
    record["grounding_status"] = quote_result.status.value
    record["grounding_similarity"] = quote_result.similarity

    participants = record.get("approx_participants")
    if participants:
        p_result = check_quote_grounding(participants, source_text)
        record["participants_grounding_status"] = p_result.status.value
    else:
        record["participants_grounding_status"] = None

    record["grounding_checker_version"] = CHECKER_VERSION
    record["review_status"] = (
        "pending_human_review" if quote_result.status.value == "FUZZY" else "not_required"
    )
    return record


def run() -> list[dict]:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    fetch_articles.ensure_all_cached()

    all_records: list[dict] = []
    for entry in manifest:
        article_id = entry["article_id"]
        source_text = _load_body_text(article_id)

        print(f"\n=== Extracting: {article_id} ({entry['title']}) ===")
        try:
            records = extract_events_from_article(article_id, source_text)
        except ExtractionError as exc:
            print(f"[FAILED] {article_id}: {exc}", file=sys.stderr)
            continue

        print(f"  {len(records)} events extracted, grounding each against source text...")
        for record in records:
            _ground_record(record, source_text)
        all_records.extend(records)

    OUTPUT_DIR.mkdir(exist_ok=True)

    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        for record in all_records:
            f.write(json.dumps(record) + "\n")
    print(f"\n[ok] wrote {len(all_records)} records to {JSONL_PATH}")

    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for record in all_records:
            writer.writerow({col: record.get(col) for col in CSV_COLUMNS})
    print(f"[ok] wrote {len(all_records)} records to {CSV_PATH}")

    _load_to_bigquery(all_records)
    _print_summary(all_records)

    return all_records


def _load_to_bigquery(records: list[dict]) -> None:
    if not records:
        print("[skip] no records to load into BigQuery.")
        return

    from google.cloud import bigquery

    from setup_bigquery import DATASET_ID, PROJECT_ID, TABLE_ID, ensure_dataset_and_table

    if not PROJECT_ID:
        print(
            "[WARNING] GCP_PROJECT_ID/GOOGLE_CLOUD_PROJECT not set -- skipping "
            "BigQuery load. Local JSONL/CSV output above is unaffected.",
            file=sys.stderr,
        )
        return

    table_ref = ensure_dataset_and_table()
    client = bigquery.Client(project=PROJECT_ID)

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )
    with open(JSONL_PATH, "rb") as f:
        load_job = client.load_table_from_file(f, table_ref, job_config=job_config)
    load_job.result()
    print(f"[ok] appended {len(records)} rows to {PROJECT_ID}.{DATASET_ID}.{TABLE_ID}")


def _print_summary(records: list[dict]) -> None:
    total = len(records)
    if total == 0:
        print("\nNo records extracted.")
        return

    counts = {"MATCHED": 0, "FUZZY": 0, "NOT_FOUND": 0}
    for r in records:
        counts[r["grounding_status"]] = counts.get(r["grounding_status"], 0) + 1

    print(f"\n=== Grounding summary ({total} records) ===")
    for status in ("MATCHED", "FUZZY", "NOT_FOUND"):
        n = counts.get(status, 0)
        pct = (n / total * 100) if total else 0
        print(f"  {status:10s}: {n:3d}  ({pct:5.1f}%)")


if __name__ == "__main__":
    run()
