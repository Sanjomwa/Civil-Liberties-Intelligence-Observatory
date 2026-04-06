"""@bruin
name: load.acled_conflict_events
type: python
image: python:3.11
connection: bigquery
description: |
  Uploads ACLED Parquet to GCS.

materialization:
  type: table
  strategy: create+replace
@bruin"""

import pandas as pd
from datetime import datetime
import os


def materialize():
    local_parquet = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/acled/acled_conflict_events.parquet"
    gcs_bucket = "civil-liberties-data"
    gcs_path = f"gs://{gcs_bucket}/acled/acled_conflict_events.parquet"

    if not os.path.exists(local_parquet):
        raise FileNotFoundError(f"Parquet not found: {local_parquet}")

    df = pd.read_parquet(local_parquet)
    print(f"✅ Loaded {len(df):,} ACLED conflict events.")

    if "extracted_at" not in df.columns:
        df["extracted_at"] = datetime.now()

    print(f"Uploading to GCS → {gcs_path}")
    df.to_parquet(gcs_path, compression="snappy", index=False)
    print("✅ Uploaded to GCS.")

    return df
