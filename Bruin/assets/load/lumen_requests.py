"""@bruin
tags:
  - publish_cloud
  - dataset_lumen_requests
name: load.lumen_requests_to_gcs
type: python
image: python:3.12
description: Uploads canonical Lumen Parquet to GCS and creates schema-stable BigQuery external table (no DuckDB).
depends:
  - raw.lumen_requests
@bruin"""

import os
import pandas as pd
from google.cloud import bigquery


PROJECT_ID = "encoded-joy-485413-k5"
GCS_BUCKET = "civil-liberties-data"

LOCAL_FILE = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/lumen/lumen_requests.parquet"
TABLE = "lumen_requests"


def resolve_env(fallback="staging"):
    for k in ("BRUIN_ENV", "BRUIN_ENVIRONMENT", "BRUIN_PIPELINE_ENVIRONMENT"):
        v = os.getenv(k)
        if v:
            return v.strip().lower()
    return fallback


ENV = resolve_env()
DATASET = f"civil_liberties_{ENV}"
GCS_OBJECT = f"{ENV}/lumen/lumen_requests.parquet"


def materialize():
    print(f"🌍 ENV: {ENV}")

    df = pd.read_parquet(LOCAL_FILE)

    # Ensure clean microsecond UTC timestamps for Parquet → BigQuery
    for col in ["date_submitted", "extracted_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True).dt.as_unit("us")

    print("📊 dtypes for GCS Parquet:\n", df.dtypes)

    # 1. Upload to GCS
    gcs_uri = f"gs://{GCS_BUCKET}/{GCS_OBJECT}"
    df.to_parquet(gcs_uri, index=False, compression="snappy")
    print(f"✅ Uploaded Parquet to: {gcs_uri}")

    # 2. Create BigQuery external table with EXPLICIT schema (no autodetect)
    schema = [
        bigquery.SchemaField("request_id", "STRING"),
        bigquery.SchemaField("country", "STRING"),
        bigquery.SchemaField("sender", "STRING"),
        bigquery.SchemaField("recipient", "STRING"),
        # ← proper TIMESTAMP(UTC)
        bigquery.SchemaField("date_submitted", "TIMESTAMP"),
        bigquery.SchemaField("period", "STRING"),
        bigquery.SchemaField("half_year_label", "STRING"),
        bigquery.SchemaField("reason", "STRING"),
        bigquery.SchemaField("request_count", "INTEGER"),
        bigquery.SchemaField("item_count", "INTEGER"),
        # ← proper TIMESTAMP(UTC)
        bigquery.SchemaField("extracted_at", "TIMESTAMP"),
    ]

    bq = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET}.{TABLE}"

    external_config = bigquery.ExternalConfig(
        bigquery.ExternalSourceFormat.PARQUET)
    external_config.source_uris = [gcs_uri]
    external_config.autodetect = False

    table = bigquery.Table(table_ref)
    table.external_data_configuration = external_config
    table.schema = schema

    try:
        bq.delete_table(table_ref, not_found_ok=True)
    except Exception:
        pass

    bq.create_table(table)
    print(f"✅ BigQuery external table ready: {table_ref}")

    # No return needed — this is now a pure side-effect task (no DuckDB load)
    return None
