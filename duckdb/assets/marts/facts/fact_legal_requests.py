"""@bruin
name: facts.legal_requests
type: python
image: python:3.11
connection: duckdb-mart
description: |
  Fact table for legal takedown requests from Lumen staging.
  Aggregates request counts by country, year, and month.

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
  - name: legal_requests
    type: INTEGER
    description: Number of legal requests submitted
@bruin"""

import pandas as pd

# Bruin runtime import, with local fallback for VS Code
try:
    from staging import lumen
except ImportError:
    import assets.staging.lumen_staging as lumen


def materialize():
    # Load staging data
    df = lumen.materialize()

    # Aggregate by country, year, month
    fact_df = df.groupby(["country", "year", "month"]).agg(
        legal_requests=("request_type", "count")
    ).reset_index()

    print(f"Legal requests fact rows: {len(fact_df)}")
    return fact_df
