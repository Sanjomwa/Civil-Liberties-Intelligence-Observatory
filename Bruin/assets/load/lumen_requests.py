"""@bruin
tags:
  - publish_cloud
  - dataset_lumen_requests
name: load.lumen_requests_to_gcs
type: python
image: python:3.12
connection: duckdb-parquet
description: |
  Uploads canonical Lumen requests parquet to env-isolated GCS path and
  refreshes BigQuery external table in staging/prod.

depends:
  - raw.lumen_requests

materialization:
  type: table
  strategy: create+replace
@bruin"""

import os
import pandas as pd
from google.cloud import bigquery


def resolve_env(fallback: str = "staging") -> str:
    for k in ("BRUIN_ENV", "BRUIN_ENVIRONMENT", "BRUIN_PIPELINE_ENVIRONMENT"):
        v = os.getenv(k)
        if v and v.strip():
            return v.strip().lower()
    return fallback


def require_cloud_env(env: str) -> None:
    if env not in ("staging", "prod"):
        raise ValueError(
            f"This load asset supports only staging/prod. Got ENV={env!r}.")


PROJECT_ID = "encoded-joy-485413-k5"
GCS_BUCKET = "civil-liberties-data"
LOCAL_FILE = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/lumen/lumen_requests.parquet"
TABLE = "lumen_requests"

ENV = resolve_env(fallback="staging")
require_cloud_env(ENV)

DATASET = "civil_liberties_prod" if ENV == "prod" else "civil_liberties_staging"
GCS_OBJECT = f"{ENV}/lumen/lumen_requests.parquet"


def validate(df: pd.DataFrame):
    required = [
        "request_id", "country", "sender", "recipient",
        "date_submitted", "period", "half_year_label",
        "reason", "request_count", "item_count", "extracted_at"
    ]

    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing column: {col}")

    for col in ["date_submitted", "extracted_at"]:
        if not pd.api.types.is_datetime64_any_dtype(df[col]):
            raise TypeError(f"{col} not datetime")
        if df[col].dt.tz is None:
            raise TypeError(f"{col} not UTC")

        if df[col].min().year < 2000:
            raise ValueError("Epoch corruption detected in SOURCE data")

    print("✅ Schema valid")


def materialize():
    print(f"🌍 Environment : {ENV}")
    print(f"📦 BQ Dataset  : {DATASET}")

    df = pd.read_parquet(LOCAL_FILE)
    print(f"📖 Rows read   : {len(df):,}")

    validate(df)

    # ─────────────────────────────────────────────────────────────
    # CRITICAL FIX: Force microsecond precision (BigQuery + Parquet)
    # This prevents the 1970-01-01 epoch bug forever.
    # ─────────────────────────────────────────────────────────────
    for col in ["date_submitted", "extracted_at"]:
        if pd.api.types.is_datetime64tz_dtype(df[col]):
            df[col] = df[col].dt.tz_convert('UTC').dt.tz_localize(None)
        df[col] = df[col].astype('datetime64[us]')

    print(f"✅ Timestamps converted to microsecond precision")
    print(f"   date_submitted range: {df['date_submitted'].min()} → {df['date_submitted'].max()}")

    gcs_uri = f"gs://{GCS_BUCKET}/{GCS_OBJECT}"
    print(f"☁️  Uploading  : {gcs_uri}")

    # Write with pyarrow engine (more reliable timestamp handling)
    df.to_parquet(
        gcs_uri,
        index=False,
        compression="snappy",
        engine="pyarrow"
    )
    print("✅ GCS upload complete")

    # Create external table (matches Google pattern exactly)
    bq = bigquery.Client(project=PROJECT_ID)
    external_config = bigquery.ExternalConfig(
        bigquery.ExternalSourceFormat.PARQUET)
    external_config.source_uris = [gcs_uri]
    external_config.autodetect = True   # ← now safe because of the fix above

    table_ref = f"{PROJECT_ID}.{DATASET}.{TABLE}"
    table_obj = bigquery.Table(table_ref)
    table_obj.external_data_configuration = external_config
    table_obj.description = (
        f"External table [{ENV}] — Lumen transparency requests. "
        f"Backed by {gcs_uri}."
    )

    try:
        bq.delete_table(table_ref)
    except Exception:
        pass

    bq.create_table(table_obj)
    print(f"✅ BigQuery external table created: {table_ref}")

    # Keep the original extracted_at from the source parquet
    # (no need to overwrite like in the Google asset)
    return df
