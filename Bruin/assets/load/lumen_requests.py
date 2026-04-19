"""@bruin
tags:
  - publish_cloud
  - dataset_lumen_requests
name: load.lumen_requests_to_gcs
type: python
image: python:3.12
description: Parquet → GCS → BigQuery external table (WITH schema firewall)
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


def resolve_env(default="staging"):
    for k in ("BRUIN_ENV", "BRUIN_ENVIRONMENT", "BRUIN_PIPELINE_ENVIRONMENT"):
        v = os.getenv(k)
        if v:
            return v.strip().lower()
    return default


ENV = resolve_env()
DATASET = f"civil_liberties_{ENV}"
GCS_OBJECT = f"{ENV}/lumen/lumen_requests.parquet"


# -----------------------------
# 🔒 SCHEMA FIREWALL (CORE FIX)
# -----------------------------
def validate_parquet(df: pd.DataFrame):
    print("🔍 Schema firewall: validating Parquet...")

    required = {
        "request_id",
        "country",
        "date_submitted",
        "extracted_at",
        "request_count",
        "item_count"
    }

    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"❌ Missing columns: {missing}")

    # TIMESTAMP SAFETY
    for col in ["date_submitted", "extracted_at"]:
        if not pd.api.types.is_datetime64_any_dtype(df[col]):
            raise TypeError(f"❌ {col} not datetime64")

        if df[col].dt.tz is None:
            raise TypeError(f"❌ {col} missing timezone (UTC required)")

        # HARD 1970 GUARD
        if df[col].min().year < 2000:
            raise ValueError(f"❌ {col} contains epoch corruption (1970 detected)")

    # DOMAIN CHECK
    if not df["country"].isin(["US", "GB", "DE", "FR", "IN", "KE"]).any():
        raise ValueError("❌ Unexpected country values")

    print("✅ Schema firewall PASSED")


def materialize():
    print(f"🌍 ENV: {ENV}")

    # Load parquet FIRST (correct order)
    df = pd.read_parquet(LOCAL_FILE)

    # 🔒 VALIDATE BEFORE ANY WRITE
    validate_parquet(df)

    print("📊 Final schema:")
    print(df.dtypes)

    # -----------------------------
    # GCS upload
    # -----------------------------
    gcs_uri = f"gs://{GCS_BUCKET}/{GCS_OBJECT}"
    df.to_parquet(gcs_uri, index=False, compression="snappy")
    print(f"✅ Uploaded: {gcs_uri}")

    # -----------------------------
    # BigQuery external table
    # -----------------------------
    schema = [
        bigquery.SchemaField("request_id", "STRING"),
        bigquery.SchemaField("country", "STRING"),
        bigquery.SchemaField("sender", "STRING"),
        bigquery.SchemaField("recipient", "STRING"),
        bigquery.SchemaField("date_submitted", "TIMESTAMP"),
        bigquery.SchemaField("period", "STRING"),
        bigquery.SchemaField("half_year_label", "STRING"),
        bigquery.SchemaField("reason", "STRING"),
        bigquery.SchemaField("request_count", "INTEGER"),
        bigquery.SchemaField("item_count", "INTEGER"),
        bigquery.SchemaField("extracted_at", "TIMESTAMP"),
    ]

    bq = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET}.{TABLE}"

    external_config = bigquery.ExternalConfig(bigquery.ExternalSourceFormat.PARQUET)
    external_config.source_uris = [gcs_uri]
    external_config.autodetect = False

    table = bigquery.Table(table_ref)
    table.external_data_configuration = external_config
    table.schema = schema

    bq.delete_table(table_ref, not_found_ok=True)
    bq.create_table(table)

    print(f"✅ BigQuery table ready: {table_ref}")

    return None
