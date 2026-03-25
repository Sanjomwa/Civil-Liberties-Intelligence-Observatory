"""@bruin
name: raw.google_transparency
type: python
image: python:3.11
connection: duckdb-default
description: |
  Ingests Google Transparency Report government takedown requests (Jun 2023–Jun 2025).
  Downloads the official CSV ZIP, extracts, and filters for the relevant two-year window.

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

import os
import zipfile
import duckdb
import pandas as pd
import requests
from datetime import datetime


def materialize():
    url = "https://storage.googleapis.com/transparencyreport/report-downloads/government-removals_2026-1-26_2026-1-26_en_v1.zip"
    print(f"Downloading Google Transparency Report ZIP from {url}")
    response = requests.get(url, timeout=300)
    response.raise_for_status()

    # Save ZIP locally
    os.makedirs("./data/google", exist_ok=True)
    zip_path = "./data/google/google_transparency.zip"
    with open(zip_path, "wb") as f:
        f.write(response.content)

    # Extract CSV
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall("./data/google")
        csv_files = [f for f in z.namelist() if f.endswith(".csv")]
        if not csv_files:
            raise RuntimeError("No CSV found in ZIP")
        csv_path = os.path.join("./data/google", csv_files[0])

    # Load CSV
    df = pd.read_csv(csv_path)
    df["extracted_at"] = datetime.now()

    # Normalize period column to string
    df["period"] = df["period"].astype(str)

    # Filter for Jun 2023 → Jun 2025
    # (Assumes period strings like "Jan-Jun 2025", "Jul-Dec 2023")
    mask = df["period"].str.contains("2023") | df["period"].str.contains("2024") | df["period"].str.contains("2025")
    df = df.loc[mask]

    # Further restrict to >= Jun 2023 and <= Jun 2025
    valid_periods = [
        "Jul-Dec 2023", "Jan-Jun 2024", "Jul-Dec 2024", "Jan-Jun 2025"
    ]
    df = df[df["period"].isin(valid_periods)]

    # Save to Parquet
    parquet_path = "./data/google/google_transparency.parquet"
    df.to_parquet(parquet_path, index=False)

    print(f"Rows ingested: {len(df)}")
    return df


# Register in DuckDB
con = duckdb.connect("duckdb-default.db")
con.execute("""
CREATE TABLE IF NOT EXISTS google_transparency AS 
SELECT * FROM parquet_scan('./data/google/google_transparency.parquet')
""")
