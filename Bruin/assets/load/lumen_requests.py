"""@bruin
tags:
  - publish_cloud
  - dataset_lumen_requests
name: load.lumen_requests_to_gcs
type: python
image: python:3.12
depends:
  - raw.lumen_requests
@bruin"""

import os
import pandas as pd
from google.cloud import bigquery


PROJECT_ID = "encoded-joy-485413-k5"
GCS_BUCKET = "civil-liberties-data"

LOCAL_FILE = "/workspaces/.../lumen_requests.parquet"
TABLE = "lumen_requests"


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
            raise ValueError("Epoch corruption detected")

    print("✅ Schema valid")


def materialize():
    df = pd.read_parquet(LOCAL_FILE)

    validate(df)

    gcs_uri = f"gs://{GCS_BUCKET}/staging/lumen/lumen_requests.parquet"
    df.to_parquet(gcs_uri, index=False, compression="snappy")

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

    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.civil_liberties_staging.{TABLE}"

    ext = bigquery.ExternalConfig("PARQUET")
    ext.source_uris = [gcs_uri]
    ext.autodetect = False

    table = bigquery.Table(table_ref, schema=schema)
    table.external_data_configuration = ext

    client.delete_table(table_ref, not_found_ok=True)
    client.create_table(table)

    print("✅ BQ external table ready")
