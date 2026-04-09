"""@bruin
name: load.acled_conflict_events_to_gcs
type: python
image: python:3.11
connection: duckdb-parquet
description: |
  Uploads ACLED conflict events Parquet to GCS.

materialization:
  type: table
  strategy: create+replace
@bruin"""

import pandas as pd
from datetime import datetime
from pathlib import Path


def materialize():
    local_parquet = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/acled/acled_conflict_events.parquet"
    gcs_path = "gs://civil-liberties-data/acled/acled_conflict_events.parquet"

    print(f"Reading: {local_parquet}")
    df = pd.read_parquet(local_parquet)

    print(f"Uploading to GCS → {gcs_path}")
    df.to_parquet(gcs_path, index=False, compression="snappy")

    print(f"✅ Uploaded {len(df):,} rows to GCS")
    df["extracted_at"] = datetime.now()
    return df
