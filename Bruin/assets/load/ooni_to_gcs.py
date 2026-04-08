"""@bruin
name: load.ooni_to_gcs
type: python
image: python:3.11
connection: duckdb-parquet
description: |
  Uploads the processed OONI Parquet to GCS (civil-liberties-data bucket).
  Runs in staging/prod environments.

materialization:
  type: table
  strategy: create+replace

columns:
  - name: measurement_id
    type: STRING
  - name: country
    type: STRING
  - name: asn
    type: INTEGER
  - name: test_name
    type: STRING
  - name: input
    type: STRING
  - name: start_time
    type: TIMESTAMP
  - name: status
    type: STRING
  - name: probe_cc
    type: STRING
  - name: probe_asn
    type: INTEGER
  - name: extracted_at
    type: TIMESTAMP
@bruin"""

import pandas as pd
from datetime import datetime
from pathlib import Path
import os


def materialize():
    local_parquet = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/ooni/ooni_measurements.parquet"
    gcs_path = "gs://civil-liberties-data/ooni/ooni_measurements.parquet"

    print(f"Reading Parquet: {local_parquet}")
    df = pd.read_parquet(local_parquet)

    print(f"Uploading to GCS → {gcs_path}")
    df.to_parquet(gcs_path, index=False, compression="snappy")

    print(f"✅ Uploaded {len(df):,} rows to {gcs_path}")

    df["extracted_at"] = datetime.now()
    return df
