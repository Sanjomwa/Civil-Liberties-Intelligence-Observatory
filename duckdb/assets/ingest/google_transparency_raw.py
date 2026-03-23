"""@bruin
name: raw.google_transparency
type: python
image: python:3.11
connection: duckdb-default
description: |
  Ingests Google Transparency Report government takedown requests (2024–2026).
  Calls the Transparency Report API, parses JSON, and filters for the relevant years.

materialization:
  type: table
  strategy: append

columns:
  - name: country
    type: VARCHAR
    description: Country of origin
  - name: period
    type: VARCHAR
    description: Six-month reporting period
  - name: request_count
    type: INTEGER
    description: Number of requests in the period
  - name: item_count
    type: INTEGER
    description: Number of items requested for removal
  - name: extracted_at
    type: TIMESTAMP
    description: Timestamp when ingested
@bruin"""

import duckdb
import pandas as pd
import requests
from datetime import datetime


def materialize():
    url = "https://transparencyreport.google.com/transparencyreport/api/v3/government-removals/overview"
    print(f"Fetching Google Transparency Report data from {url}")
    response = requests.get(url, timeout=300)
    response.raise_for_status()

    data = response.json()

    # Normalize JSON into DataFrame
    df = pd.json_normalize(data, record_path=["data"], meta=[
                           "country", "period"])
    df["extracted_at"] = datetime.now()

    # Filter for 2024–2026
    df["period"] = df["period"].astype(str)
    mask = df["period"].str.contains("2024|2025|2026")
    df = df.loc[mask]

    # Save to Parquet
    df.to_parquet("./data/google/google_transparency.parquet", index=False)

    print(f"Rows ingested: {len(df)}")
    return df


con = duckdb.connect("duckdb-default.db")
con.execute("""
CREATE TABLE IF NOT EXISTS google_transparency AS 
SELECT * FROM parquet_scan('./data/google/google_transparency.parquet')
""")
