"""
setup_bigquery.py — OTF-04 LLM extraction prototype

Creates the dedicated `llm_derived` BigQuery dataset and its
`article_extractions` table, deliberately outside every existing CLIO
dataset (civil_liberties_prod/staging, features, int, intelligence, marts,
reporting) and outside Bruin's DAG entirely.

WHY THIS IS NOT A BRUIN ASSET (see ADR-0009 for the full reasoning): LLM
calls are nondeterministic and billed per run. Bruin's rebuild/backfill
execution model would silently re-invoke and re-bill extract_openai.py on
every DAG rebuild if this were wired in as a `type: python` asset with
declared dependents. This script -- and run_extraction.py, which loads
into the table this script creates -- are run manually only:

    python llm_extraction/setup_bigquery.py       # once, or safely re-run (idempotent)
    python llm_extraction/run_extraction.py        # each real extraction run

Location: this project's existing datasets (civil_liberties_prod,
civil_liberties_staging, features, int, intelligence, marts, reporting)
all live in us-central1 (confirmed live via `bq ls --format=prettyjson`
before writing this file, not assumed) -- llm_derived matches that
location for operational consistency, though it is a fully separate
dataset with its own access surface.

Safe to re-run: dataset and table creation both use exists_ok semantics.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")

PROJECT_ID = os.environ.get("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = "us-central1"  # matches every existing CLIO dataset's live location
DATASET_ID = "llm_derived"
TABLE_ID = "article_extractions"

TABLE_SCHEMA = [
    bigquery.SchemaField("source_article_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("event_date", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("location_text", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("approx_participants", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("event_type", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("description", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("verbatim_quote", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("grounding_status", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("grounding_similarity", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("participants_grounding_status", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("llm_derived", "BOOL", mode="REQUIRED"),
    bigquery.SchemaField("extraction_model", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("extraction_timestamp_utc", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("prompt_version_hash", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("grounding_checker_version", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("review_status", "STRING", mode="REQUIRED"),
]


def ensure_dataset_and_table() -> bigquery.TableReference:
    if not PROJECT_ID:
        print(
            "FATAL: neither GCP_PROJECT_ID nor GOOGLE_CLOUD_PROJECT is set in "
            "the environment/.env. Cannot determine which BigQuery project to "
            "create llm_derived in.",
            file=sys.stderr,
        )
        sys.exit(1)

    client = bigquery.Client(project=PROJECT_ID)

    dataset_ref = bigquery.DatasetReference(PROJECT_ID, DATASET_ID)
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = LOCATION
    dataset.description = (
        "OTF-04 LLM extraction prototype output. Every row carries "
        "llm_derived=true and is disclosed, non-authoritative, and never "
        "joined into composite_pressure_score, fact_country_pressure_daily, "
        "or the ACLED regime engine's output without a future ADR "
        "explicitly superseding ADR-0009. Deliberately outside Bruin's DAG "
        "-- see ADR-0009 and llm_extraction/README.md."
    )
    dataset = client.create_dataset(dataset, exists_ok=True)
    print(f"[ok] dataset {PROJECT_ID}.{DATASET_ID} ready (location={dataset.location})")

    table_ref = dataset_ref.table(TABLE_ID)
    table = bigquery.Table(table_ref, schema=TABLE_SCHEMA)
    table.description = (
        "Append-only log of OTF-04 LLM extraction runs -- a running log of "
        "extraction attempts, not a point-in-time snapshot. Never "
        "create+replace this table; always append."
    )
    table = client.create_table(table, exists_ok=True)
    print(f"[ok] table {PROJECT_ID}.{DATASET_ID}.{TABLE_ID} ready ({len(table.schema)} columns)")

    return table_ref


if __name__ == "__main__":
    ensure_dataset_and_table()
