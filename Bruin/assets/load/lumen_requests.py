"""@bruin
name: load.lumen_requests_to_gcs
type: python
image: python:3.11
connection: duckdb-parquet
description: |
  Uploads Lumen mock takedown requests Parquet to GCS.

materialization:
  type: table
  strategy: create+replace
@bruin"""

import pandas as pd
from datetime import datetime
from pathlib import Path


def materialize():
    local_parquet = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/lumen/lumen_requests.parquet"
    gcs_path = "gs://civil-liberties-data/lumen/lumen_requests.parquet"

    print(f"Reading: {local_parquet}")
    df = pd.read_parquet(local_parquet)

    print(f"Uploading to GCS → {gcs_path}")
    df.to_parquet(gcs_path, index=False, compression="snappy")

    print(f"✅ Uploaded {len(df):,} rows to GCS")
    df["extracted_at"] = datetime.now()
    return df
