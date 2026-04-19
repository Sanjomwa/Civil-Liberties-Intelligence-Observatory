"""@bruin
tags:
  - publish_cloud
  - dataset_lumen_requests
name: load.lumen_requests_to_gcs
type: python
image: python:3.12
connection: duckdb-parquet
description: Uploads canonical Lumen mock parquet to GCS and refreshes BigQuery external table.
depends:
  - raw.lumen_requests
materialization:
  type: table
  strategy: create+replace
@bruin"""

import os
import pandas as pd
from datetime import datetime
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

    # FIX 1: normalize timestamps (CRITICAL)
    for col in ["date_submitted", "extracted_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True).dt.floor("us")

    print(df.dtypes)

    gcs_uri = f"gs://{GCS_BUCKET}/{GCS_OBJECT}"

    df.to_parquet(gcs_uri, index=False, compression="snappy")

    bq = bigquery.Client(project=PROJECT_ID)

    table_ref = f"{PROJECT_ID}.{DATASET}.{TABLE}"

    external_config = bigquery.ExternalConfig(
        bigquery.ExternalSourceFormat.PARQUET
    )
    external_config.source_uris = [gcs_uri]
    external_config.autodetect = True

    table = bigquery.Table(table_ref)
    table.external_data_configuration = external_config

    # SAFE DROP
    try:
        bq.delete_table(table_ref, not_found_ok=True)
    except Exception:
        pass

    bq.create_table(table)

    print(f"✅ Loaded: {table_ref}")

    return df
