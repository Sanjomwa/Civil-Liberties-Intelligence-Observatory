"""@bruin
name: raw.acled_aggregated
type: python
image: python:3.11
connection: duckdb-default
description: |
  Ingests ACLED aggregated conflict data (Africa).
  Downloads aggregated CSV file from ACLED portal.
  Returns a Pandas DataFrame for Bruin to append into DuckDB.

materialization:
  type: table
  strategy: append

columns:
  - name: country
    type: VARCHAR
    description: Country where the events occurred
  - name: admin1
    type: VARCHAR
    description: First-level administrative division
  - name: event_type
    type: VARCHAR
    description: Type of event (e.g. battles, protests)
  - name: fatalities
    type: INTEGER
    description: Number of reported fatalities
  - name: event_count
    type: INTEGER
    description: Number of events in the aggregation
  - name: year
    type: INTEGER
    description: Year of the aggregated data
  - name: month
    type: INTEGER
    description: Month of the aggregated data
  - name: extracted_at
    type: TIMESTAMP
    description: Timestamp when the data was ingested
@bruin"""

import duckdb
import pandas as pd
import requests
import io
from datetime import datetime


def materialize():
    # ACLED aggregated Africa dataset URL
    url = "https://acleddata.com/aggregated/aggregated-data-africa.csv"
    print(f"Downloading {url}")

    response = requests.get(url, timeout=300)
    response.raise_for_status()

    df = pd.read_csv(io.BytesIO(response.content))
    # Normalize column names
    df.columns = df.columns.str.lower().str.replace(" ", "_")
    df["extracted_at"] = datetime.now()

    # Filter for 2024–2026
    df = df[df["year"].between(2024, 2026)]

    # Save to Parquet
    df.to_parquet("./data/acled/acled.parquet", index=False)

    print(f"Rows ingested: {len(df)}")
    return df


con = duckdb.connect("duckdb-default.db")
con.execute("""
CREATE TABLE IF NOT EXISTS acled_aggregated AS 
SELECT * FROM parquet_scan('./data/acled/acled.parquet')
""")
