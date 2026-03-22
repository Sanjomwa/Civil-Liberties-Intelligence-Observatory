"""@bruin
name: facts.takedown_requests
type: python
image: python:3.11
connection: duckdb-mart
description: |
  Fact table for government takedown requests from Google Transparency staging.
  Aggregates request counts and items requested by country, year, and month.

materialization:
  type: table
  strategy: overwrite

columns:
  - name: country
    type: VARCHAR
    description: Country key
  - name: year
    type: INTEGER
    description: Year of aggregation
  - name: month
    type: INTEGER
    description: Month of aggregation
  - name: takedown_requests
    type: INTEGER
    description: Number of takedown requests
  - name: items_requested
    type: INTEGER
    description: Number of items requested for removal
@bruin"""

import pandas as pd

# Bruin runtime import, with local fallback for VS Code
try:
    from staging import google_transparency
except ImportError:
    import assets.staging.google_transparency_staging as google_transparency


def materialize():
    # Load staging data
    df = google_transparency.materialize()

    # Aggregate by country, year, month
    fact_df = df.groupby(["country", "year", "month"]).agg(
        takedown_requests=("request_count", "sum"),
        items_requested=("items_requested", "sum")
    ).reset_index()

    print(f"Takedown requests fact rows: {len(fact_df)}")
    return fact_df
