"""@bruin
name: staging.lumen
type: python
image: python:3.11
connection: duckdb-lumen
description: |
  Cleans and normalizes Lumen raw data.
  Ensures consistent schema for downstream mart joins.

materialization:
  type: table
  strategy: overwrite

columns:
  - name: country
    type: VARCHAR
    description: Country where the takedown request originated
  - name: sender
    type: VARCHAR
    description: Entity submitting the request (e.g. government, corporation)
  - name: recipient
    type: VARCHAR
    description: Platform or service receiving the request
  - name: request_type
    type: VARCHAR
    description: Type of request (court order, DMCA, etc.)
  - name: content_url
    type: VARCHAR
    description: URL of the content targeted for removal
  - name: date_submitted
    type: DATE
    description: Date when the request was submitted
  - name: extracted_at
    type: TIMESTAMP
    description: Timestamp when the data was ingested
@bruin"""

import pandas as pd

# Bruin runtime import, with local fallback for VS Code
try:
    from ingest import lumen_raw
except ImportError:
    import assets.ingest.lumen_raw as lumen_raw


def materialize():
    # Load from the raw asset
    df = lumen_raw.materialize()

    # Example staging transformations:
    # - Drop duplicates
    # - Normalize text fields
    # - Ensure proper dtypes for dates
    df = df.drop_duplicates()
    df["sender"] = df["sender"].str.lower().str.strip()
    df["recipient"] = df["recipient"].str.lower().str.strip()
    df["request_type"] = df["request_type"].str.lower().str.strip()
    df["date_submitted"] = pd.to_datetime(
        df["date_submitted"], errors="coerce").dt.date

    # Optional: filter by country variable
    import os
    country = os.getenv("BRUIN_COUNTRY", "Kenya")
    df = df[df["country"].str.lower() == country.lower()]

    print(f"Lumen staging rows: {len(df)}")
    return df
