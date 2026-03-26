"""@bruin
name: raw.google_transparency_requests
type: python
image: python:3.11
connection: duckdb-parquet
description: Ingest Google Transparency requests CSV into raw table and export as Parquet

materialization:
  type: table
  strategy: create+replace   # overwrite instead of append

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

import duckdb
import os
import pandas as pd
from datetime import datetime


def materialize():
    db_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/civil_liberties_dev.db"
    conn = duckdb.connect(db_path)

    base_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/google/"
    requests_csv = os.path.join(
        base_path, "google-government-removal-requests.csv")
    parquet_out = os.path.join(
        base_path, "google_transparency_requests.parquet")

    df = conn.execute("""
        SELECT 
            country,
            product,
            reason,
            time_period,
            number_of_requests,
            items_requested_removal,
            CURRENT_TIMESTAMP AS extracted_at
        FROM read_csv_auto(?)
    """, [requests_csv]).df()

    # Save to Parquet
    df.to_parquet(parquet_out, index=False)

    print(f"✅ Ingested {len(df)} rows into google_transparency_requests")
    return df
