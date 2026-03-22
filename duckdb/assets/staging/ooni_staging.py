"""@bruin
name: staging.ooni
type: python
image: python:3.11
connection: duckdb-ooni
description: |
  Cleans and normalizes OONI raw data.
  Ensures consistent schema for downstream mart joins.

materialization:
  type: table
  strategy: overwrite

columns:
  - name: country
    type: VARCHAR
    description: Country where the test was run
  - name: test_name
    type: VARCHAR
    description: Name of the OONI test
  - name: result
    type: VARCHAR
    description: Outcome of the test (e.g. blocked, ok)
  - name: start_time
    type: TIMESTAMP
    description: When the test started
  - name: end_time
    type: TIMESTAMP
    description: When the test ended
  - name: extracted_at
    type: TIMESTAMP
    description: Timestamp when the data was ingested
@bruin"""

import pandas as pd

# Bruin runtime import, with local fallback for VS Code
try:
    from raw import ooni_raw
except ImportError:
    import assets.raw.ooni_raw as ooni_raw


def materialize():
    # Load from the raw asset
    df = ooni_raw.materialize()

    # Example staging transformations:
    # - Drop duplicates
    # - Normalize test names
    # - Ensure timestamps are proper datetime objects
    df = df.drop_duplicates()
    df["test_name"] = df["test_name"].str.lower().str.strip()
    df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
    df["end_time"] = pd.to_datetime(df["end_time"], errors="coerce")

    # Optional: filter by country variable
    import os
    country = os.getenv("BRUIN_COUNTRY", "Kenya")
    df = df[df["country"].str.lower() == country.lower()]

    print(f"OONI staging rows: {len(df)}")
    return df
