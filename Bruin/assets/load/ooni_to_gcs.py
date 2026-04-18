"""@bruin
tags:
  - publish_cloud
  - dataset_ooni_conflict_measurements
name: load.ooni_to_gcs
type: python
image: python:3.12
connection: duckdb-parquet
description: |
  Uploads canonical OONI parquet to env-isolated GCS path and refreshes
  BigQuery external table in staging/prod.

depends:
  - raw.ooni_conflict_measurements

materialization:
  type: table
  strategy: create+replace
@bruin"""

import os
import sys
from datetime import datetime

import pandas as pd
from google.cloud import storage, bigquery


PROJECT_ID = "encoded-joy-485413-k5"
GCS_BUCKET = "civil-liberties-data"
LOCAL_FILE = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/ooni/ooni_measurements.parquet"
TABLE = "ooni_measurements"


# -----------------------------
# ENV RESOLUTION (FIXED)
# -----------------------------
def resolve_env() -> str:
    # 1. explicit override
    env = os.getenv("TARGET_ENV")
    if env:
        return env.strip().lower()

    # 2. bruin env vars (if ever set)
    for key in (
        "BRUIN_ENV",
        "BRUIN_ENVIRONMENT",
        "BRUIN_PIPELINE_ENVIRONMENT",
    ):
        val = os.getenv(key)
        if val:
            return val.strip().lower()

    # 3. CLI args fallback (critical fix)
    for arg in sys.argv:
        if "prod" in arg.lower():
            return "prod"
        if "staging" in arg.lower():
            return "staging"

    # ❌ NEVER silently fallback
    raise RuntimeError(
        "Environment not detected. "
        "Use TARGET_ENV=prod or staging."
    )


def require_cloud_env(env: str):
    if env not in ("staging", "prod"):
        raise ValueError(f"Invalid ENV: {env}")

    print(f"[SAFE] Running in {env.upper()}")


ENV = resolve_env()
require_cloud_env(ENV)

DATASET = "civil_liberties_prod" if ENV == "prod" else "civil_liberties_staging"
GCS_OBJECT = f"{ENV}/ooni/ooni_measurements.parquet"


# -----------------------------
# GCS UPLOAD (STREAMING)
# -----------------------------
def upload_to_gcs():
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_OBJECT)

    print(f"Uploading to gs://{GCS_BUCKET}/{GCS_OBJECT}")
    blob.upload_from_filename(LOCAL_FILE)


# -----------------------------
# BQ EXTERNAL TABLE
# -----------------------------
def create_external_table():
    bq = bigquery.Client(project=PROJECT_ID)

    gcs_uri = f"gs://{GCS_BUCKET}/{GCS_OBJECT}"
    table_ref = f"{PROJECT_ID}.{DATASET}.{TABLE}"

    external_config = bigquery.ExternalConfig(
        bigquery.ExternalSourceFormat.PARQUET
    )
    external_config.source_uris = [gcs_uri]
    external_config.autodetect = True

    table = bigquery.Table(table_ref)
    table.external_data_configuration = external_config

    try:
        bq.delete_table(table_ref)
    except Exception:
        pass

    bq.create_table(table)
    print(f"Created table: {table_ref}")


# -----------------------------
# ENTRYPOINT
# -----------------------------
def materialize():
    print(f"ENV: {ENV}")

    upload_to_gcs()
    create_external_table()

    return pd.DataFrame([
        {
            "status": "success",
            "env": ENV,
            "gcs_path": f"gs://{GCS_BUCKET}/{GCS_OBJECT}",
            "table": f"{PROJECT_ID}.{DATASET}.{TABLE}",
            "loaded_at": datetime.utcnow(),
        }
    ])
