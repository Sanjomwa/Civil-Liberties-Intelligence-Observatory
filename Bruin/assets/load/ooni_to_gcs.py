"""@bruin
name: load.ooni_to_gcs
type: python
image: python:3.12
connection: duckdb-parquet

tags:
  - publish_cloud
  - dataset_ooni

description: |
  Uploads canonical OONI Parquet to GCS and refreshes the BigQuery external
  table used by staging models.

depends:
  - raw.ooni_conflict_measurements

materialization:
  type: table
  strategy: create+replace
@bruin"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from google.cloud import bigquery, storage


PROJECT_ID = "encoded-joy-485413-k5"
GCS_BUCKET = "civil-liberties-data"
LOCAL_FILE = Path(
    "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/ooni/ooni_measurements.parquet"
)
TABLE = "ooni_measurements"


def resolve_env() -> str:
    env = os.getenv("TARGET_ENV")
    if env:
        env = env.strip().lower()
    else:
        env = ""
        for arg in sys.argv:
            if "prod" in arg.lower():
                env = "prod"
            if "staging" in arg.lower():
                env = "staging"

    if env not in {"staging", "prod"}:
        raise RuntimeError(
            "Environment not detected. Use TARGET_ENV=prod or TARGET_ENV=staging.")
    return env


def materialize() -> pd.DataFrame:
    env = resolve_env()
    dataset = "civil_liberties_prod" if env == "prod" else "civil_liberties_staging"
    gcs_object = f"{env}/ooni/ooni_measurements.parquet"
    gcs_uri = f"gs://{GCS_BUCKET}/{gcs_object}"
    table_ref = f"{PROJECT_ID}.{dataset}.{TABLE}"

    if not LOCAL_FILE.exists():
        raise FileNotFoundError(f"Missing local OONI Parquet: {LOCAL_FILE}")

    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET)
    bucket.blob(gcs_object).upload_from_filename(str(LOCAL_FILE))

    bq = bigquery.Client(project=PROJECT_ID)
    external_config = bigquery.ExternalConfig(
        bigquery.ExternalSourceFormat.PARQUET)
    external_config.source_uris = [gcs_uri]
    external_config.autodetect = True

    table = bigquery.Table(table_ref)
    table.external_data_configuration = external_config

    try:
        bq.delete_table(table_ref)
    except Exception:
        pass

    bq.create_table(table)

    return pd.DataFrame(
        [
            {
                "status": "success",
                "env": env,
                "gcs_uri": gcs_uri,
                "table_ref": table_ref,
                "loaded_at": datetime.now(timezone.utc),
            }
        ]
    )
