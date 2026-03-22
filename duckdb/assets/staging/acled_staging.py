"""@bruin
name: staging.acled
type: python
image: python:3.11
connection: duckdb-acled
description: |
  Cleans and normalizes ACLED aggregated raw data.
  Ensures consistent schema for downstream mart joins.

materialization:
  type: table
  strategy: overwrite

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

import pandas as pd


def materialize():
    # Load from the raw asset
    from raw import acled_aggregated

    df = acled_aggregated.materialize()

    # Example staging transformations:
    # - Drop duplicates
    # - Ensure proper dtypes
    # - Normalize event_type values
    df = df.drop_duplicates()
    df["event_type"] = df["event_type"].str.lower().str.strip()
    df["year"] = df["year"].astype(int)
    df["month"] = df["month"].astype(int)

    # Optional: filter by country variable if passed in
    # (Bruin injects pipeline variables as environment variables)
    import os
    country = os.getenv("BRUIN_COUNTRY", "Kenya")
    df = df[df["country"].str.lower() == country.lower()]

    print(f"ACLED staging rows: {len(df)}")
    return df
