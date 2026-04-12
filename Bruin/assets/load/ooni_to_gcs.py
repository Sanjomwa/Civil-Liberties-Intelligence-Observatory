"""@bruin
name: load.ooni_to_gcs
type: python
image: python:3.11
connection: duckdb-parquet
description: |
  Uploads OONI Parquet to GCS and creates/refreshes a BigQuery external table
  pointing at gs://civil-liberties-data/ooni/. No data is duplicated — BQ
  reads directly from the Parquet file on GCS (cost-effective).

depends:
  - raw.ooni_conflict_measurements

materialization:
  type: table
  strategy: create+replace
@bruin"""

import os
import pandas as pd
from datetime import datetime
from google.cloud import bigquery, storage


PROJECT_ID = "encoded-joy-485413-k5"
DATASET = "civil_liberties_staging"
TABLE = "ooni_measurements"
GCS_BUCKET = "civil-liberties-data"
GCS_OBJECT = "ooni/ooni_measurements.parquet"
LOCAL_FILE = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/ooni/ooni_measurements.parquet"


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
        "External table — OONI Kenya censorship measurements (Jun 2023–Jun 2025). "
        "Data lives in GCS; BigQuery reads it on query."
    )

    # delete if exists so we can recreate with fresh schema
    try:
        bq.delete_table(table_ref)
        print(f"🗑️  Dropped existing BQ table: {table_ref}")
    except Exception:
        pass  # table didn't exist yet

    bq.create_table(table_obj)
    print(f"✅ BigQuery external table created: {table_ref}")
    print(f"   Source URI : {gcs_uri}")
    print(f"   Rows       : {len(df):,}")

    df["extracted_at"] = datetime.now()
    return df
