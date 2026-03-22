"""@bruin
name: staging.google_transparency
type: python
image: python:3.11
connection: duckdb-google
description: |
  Cleans and normalizes Google Transparency raw data.
  Ensures consistent schema for downstream mart joins.

materialization:
  type: table
  strategy: overwrite

columns:
  - name: country
    type: VARCHAR
    description: Country where the takedown request originated
  - name: request_type
    type: VARCHAR
    description: Type of request (court order, government request, etc.)
  - name: content_type
    type: VARCHAR
    description: Type of content targeted (video, search result, etc.)
  - name: request_count
    type: INTEGER
    description: Number of requests in the reporting period
  - name: items_requested
    type: INTEGER
    description: Number of items requested for removal
  - name: period_start
    type: DATE
    description: Start date of the reporting period
  - name: period_end
    type: DATE
    description: End date of the reporting period
  - name: extracted_at
    type: TIMESTAMP
    description: Timestamp when the data was ingested
@bruin"""

import pandas as pd

# Bruin runtime import, with local fallback for VS Code
try:
    from ingest import google_transparency_raw
except ImportError:
    import assets.ingest.google_transparency_raw as google_transparency_raw


def materialize():
    # Load from the raw asset
    df = google_transparency_raw.materialize()

    # Example staging transformations:
    # - Drop duplicates
    # - Normalize request_type and content_type values
    # - Ensure proper dtypes for counts and dates
    df = df.drop_duplicates()
    df["request_type"] = df["request_type"].str.lower().str.strip()
    df["content_type"] = df["content_type"].str.lower().str.strip()
    df["request_count"] = pd.to_numeric(
        df["request_count"], errors="coerce").fillna(0).astype(int)
    df["items_requested"] = pd.to_numeric(
        df["items_requested"], errors="coerce").fillna(0).astype(int)
    df["period_start"] = pd.to_datetime(
        df["period_start"], errors="coerce").dt.date
    df["period_end"] = pd.to_datetime(
        df["period_end"], errors="coerce").dt.date

    # Optional: filter by country variable
    import os
    country = os.getenv("BRUIN_COUNTRY", "Kenya")
    df = df[df["country"].str.lower() == country.lower()]

    print(f"Google Transparency staging rows: {len(df)}")
    return df
