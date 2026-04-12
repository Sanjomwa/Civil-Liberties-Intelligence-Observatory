"""@bruin
name: load.acled_conflict_events_to_gcs
type: python
image: python:3.11
connection: duckdb-parquet
description: |
  Uploads ACLED conflict events Parquet to GCS and creates/refreshes a
  BigQuery external table. BQ reads directly from GCS — no duplication.

depends:
  - raw.acled_conflict_events

materialization:
  type: table
  strategy: create+replace
@bruin"""

import pandas as pd
from datetime import datetime
from google.cloud import bigquery


PROJECT_ID = "encoded-joy-485413-k5"
DATASET = "civil_liberties_staging"
TABLE = "acled_conflict_events"
GCS_BUCKET = "civil-liberties-data"
GCS_OBJECT = "acled/acled_conflict_events.parquet"
LOCAL_FILE = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/acled/acled_conflict_events.parquet"


def materialize():
    # ── 1. Read local Parquet ────────────────────────────────────────────────
    print(f"📖 Reading: {LOCAL_FILE}")
    df = pd.read_parquet(LOCAL_FILE)
    print(f"   Rows: {len(df):,}")

    # ── 2. Upload to GCS ─────────────────────────────────────────────────────
    gcs_uri = f"gs://{GCS_BUCKET}/{GCS_OBJECT}"
    print(f"☁️  Uploading to {gcs_uri}")
    df.to_parquet(gcs_uri, index=False, compression="snappy")
    print(f"✅ GCS upload complete")

    # ── 3. Create / replace BigQuery external table ──────────────────────────
    bq = bigquery.Client(project=PROJECT_ID)

    external_config = bigquery.ExternalConfig(
        bigquery.ExternalSourceFormat.PARQUET)
    external_config.source_uris = [gcs_uri]
    external_config.autodetect = True

    table_ref = f"{PROJECT_ID}.{DATASET}.{TABLE}"
    table_obj = bigquery.Table(table_ref)
    table_obj.external_data_configuration = external_config
    table_obj.description = (
        "External table — ACLED Kenya conflict events (Jun 2023–Jun 2025). "
        "Data lives in GCS; BigQuery reads it on query."
    )

    try:
        bq.delete_table(table_ref)
        print(f"🗑️  Dropped existing BQ table: {table_ref}")
    except Exception:
        pass

    bq.create_table(table_obj)
    print(f"✅ BigQuery external table created: {table_ref}")
    print(f"   Source URI : {gcs_uri}")
    print(f"   Rows       : {len(df):,}")

    df["extracted_at"] = datetime.now()
    return df
