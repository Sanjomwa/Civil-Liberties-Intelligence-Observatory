"""@bruin
name: raw.google_transparency_detailed
type: python
image: python:3.11
connection: duckdb-parquet
description: Ingest Google Transparency detailed removal requests CSV into raw table and export as Parquet

materialization:
  type: table
  strategy: create+replace   # overwrite instead of append

columns:
  - name: country_region
    type: STRING
    description: Country or region issuing request
  - name: period_ending
    type: STRING
    description: Period ending date
  - name: product
    type: STRING
    description: Google product targeted
  - name: reason
    type: STRING
    description: Reason for takedown
  - name: total
    type: INTEGER
    description: Total requests
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
    detailed_csv = os.path.join(
        base_path, "google-government-detailed-removal-requests.csv")
    parquet_out = os.path.join(
        base_path, "google_transparency_detailed.parquet")

    df = conn.execute("""
        SELECT 
            "Country/Region" AS country_region,
            "Period Ending" AS period_ending,
            Product,
            Reason,
            Total,
            CURRENT_TIMESTAMP AS extracted_at
        FROM read_csv_auto(?)
    """, [detailed_csv]).df()

    # Save to Parquet
    df.to_parquet(parquet_out, index=False)

    print(f"✅ Ingested {len(df)} rows into google_transparency_detailed")
    return df
