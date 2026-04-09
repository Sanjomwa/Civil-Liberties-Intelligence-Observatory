"""@bruin
name: raw.google_transparency_requests
type: python
image: python:3.11
connection: duckdb-parquet
description: Ingests Google Transparency removal requests CSV and exports as Parquet.

materialization:
  type: table
  strategy: create+replace

columns:
  - name: country
    type: STRING
    description: Country issuing request
  - name: product
    type: STRING
    description: Google product targeted
  - name: reason
    type: STRING
    description: Reason for takedown
  - name: time_period
    type: STRING
    description: Reporting period
  - name: number_of_requests
    type: INTEGER
    description: Number of requests
  - name: items_requested_removal
    type: INTEGER
    description: Items requested for removal
  - name: extracted_at
    type: TIMESTAMP
    description: Pipeline extraction timestamp
@bruin"""

import pandas as pd
from datetime import datetime
from pathlib import Path


def materialize():
    base_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/google"
    csv_file = Path(base_path) / "google-government-removal-requests.csv"
    parquet_out = Path(base_path) / "google_transparency_requests.parquet"

    print(f"📂 Reading Google requests CSV: {csv_file.name}")

    df = pd.read_csv(csv_file)

    df["extracted_at"] = datetime.now()

    df.to_parquet(parquet_out, index=False, compression="snappy")

    print(f"✅ Ingested {len(df):,} rows → google_transparency_requests")
    return df
