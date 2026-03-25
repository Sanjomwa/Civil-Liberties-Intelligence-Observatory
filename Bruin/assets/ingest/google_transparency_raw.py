"""@bruin
name: raw.google_transparency
type: python
image: python:3.11
connection: duckdb-default
description: |
  Ingests Google Transparency Report government takedown requests (Jun 2023–Jun 2025).
  Extracts both overview and detailed CSVs from the official ZIP dataset.

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
  - name: product
    type: VARCHAR
    description: Platform targeted
  - name: reason
    type: VARCHAR
    description: Legal or policy grounds
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

    # Extract CSVs
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall("./data/google")
        files = z.namelist()

    # --- Overview file ---
    overview_file = [f for f in files if "government-removal-requests" in f and f.endswith(".csv")]
    if overview_file:
        df_overview = pd.read_csv(os.path.join("./data/google", overview_file[0]))
        df_overview["extracted_at"] = datetime.now()

        # Filter for Jun 2023 → Jun 2025
        valid_periods = ["Jul-Dec 2023", "Jan-Jun 2024", "Jul-Dec 2024", "Jan-Jun 2025"]
        df_overview = df_overview[df_overview["time_period"].isin(valid_periods)]

        df_overview.to_parquet("./data/google/google_transparency_requests.parquet", index=False)
        print(f"Overview rows ingested: {len(df_overview)}")

    # --- Detailed file ---
    detailed_file = [f for f in files if "government-detailed-removal-requests" in f and f.endswith(".csv")]
    if detailed_file:
        df_detailed = pd.read_csv(os.path.join("./data/google", detailed_file[0]))
        df_detailed["extracted_at"] = datetime.now()

        # Filter for Jun 2023 → Jun 2025
        valid_periods = ["Jul-Dec 2023", "Jan-Jun 2024", "Jul-Dec 2024", "Jan-Jun 2025"]
        df_detailed = df_detailed[df_detailed["Period Ending"].isin(valid_periods)]

        df_detailed.to_parquet("./data/google/google_transparency_detailed.parquet", index=False)
        print(f"Detailed rows ingested: {len(df_detailed)}")

    return {"overview": len(df_overview), "detailed": len(df_detailed)}


# Register in DuckDB
con = duckdb.connect("duckdb-default.db")
con.execute("""
CREATE TABLE IF NOT EXISTS google_transparency_requests AS 
SELECT * FROM parquet_scan('./data/google/google_transparency_requests.parquet')
""")
con.execute("""
CREATE TABLE IF NOT EXISTS google_transparency_detailed AS 
SELECT * FROM parquet_scan('./data/google/google_transparency_detailed.parquet')
""")
