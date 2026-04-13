"""@bruin
tags:
  - publish_cloud
  - dataset_google_transparency_detailed
name: load.google_transparency_detailed_to_gcs
type: python
image: python:3.12
connection: duckdb-parquet
description: |
  Uploads canonical Google detailed parquet to env-isolated GCS path and
  refreshes BigQuery external table in staging/prod.

depends:
  - raw.google_transparency_detailed

materialization:
  type: table
  strategy: create+replace
@bruin"""

import pandas as pd
from datetime import datetime
from google.cloud import bigquery
from _env import resolve_env, require_cloud_env

PROJECT_ID = "encoded-joy-485413-k5"
GCS_BUCKET = "civil-liberties-data"
LOCAL_FILE = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/google/google_transparency_detailed.parquet"
TABLE = "google_transparency_detailed"

ENV = resolve_env(fallback="staging")
require_cloud_env(ENV)

DATASET = "civil_liberties_prod" if ENV == "prod" else "civil_liberties_staging"
GCS_OBJECT = f"{ENV}/google/google_transparency_detailed.parquet"


def materialize():
    print(f"🌍 Environment : {ENV}")
    print(f"📦 BQ Dataset  : {DATASET}")

    df = pd.read_parquet(LOCAL_FILE)
    print(f"📖 Rows read   : {len(df):,}")

    gcs_uri = f"gs://{GCS_BUCKET}/{GCS_OBJECT}"
    print(f"☁️  Uploading  : {gcs_uri}")
    df.to_parquet(gcs_uri, index=False, compression="snappy")
    print("✅ GCS upload complete")

    bq = bigquery.Client(project=PROJECT_ID)
    external_config = bigquery.ExternalConfig(bigquery.ExternalSourceFormat.PARQUET)
    external_config.source_uris = [gcs_uri]
    external_config.autodetect = True

    table_ref = f"{PROJECT_ID}.{DATASET}.{TABLE}"
    table_obj = bigquery.Table(table_ref)
    table_obj.external_data_configuration = external_config
    table_obj.description = (
        f"External table [{ENV}] — Google Transparency detailed requests. "
        f"Backed by {gcs_uri}."
    )

    try:
        bq.delete_table(table_ref)
    except Exception:
        pass

    bq.create_table(table_obj)
    print(f"✅ BigQuery external table created: {table_ref}")

    df["extracted_at"] = datetime.now()
    return df
