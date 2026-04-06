"""@bruin
name: load.ooni_to_gcs
type: python
image: python:3.11
connection: bigquery
description: |
  Uploads OONI Parquet to GCS.

materialization:
  type: table
  strategy: create+replace
@bruin"""

import pandas as pd
from datetime import datetime
import os


def materialize():
    local_parquet = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/ooni/ooni_measurements.parquet"
    gcs_bucket = "civil-liberties-data"          # ← Your bucket
    gcs_path = f"gs://{gcs_bucket}/ooni/ooni_measurements.parquet"

    if not os.path.exists(local_parquet):
        raise FileNotFoundError(f"Parquet not found: {local_parquet}")

    print(f"Reading {local_parquet}")
    df = pd.read_parquet(local_parquet)
    print(f"✅ Loaded {len(df):,} OONI rows.")

    if "extracted_at" not in df.columns:
        df["extracted_at"] = datetime.now()

    print(f"Uploading to GCS → {gcs_path}")
    df.to_parquet(gcs_path, compression="snappy", index=False)
    print("✅ Uploaded to GCS successfully.")

    return df
