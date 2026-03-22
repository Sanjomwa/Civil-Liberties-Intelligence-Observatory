"""@bruin
name: facts.censorship_tests
type: python
image: python:3.11
connection: duckdb-mart
description: |
  Fact table for censorship tests from OONI staging.
  Aggregates test counts and blocked outcomes by country, year, and month.

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
  - name: censorship_tests
    type: INTEGER
    description: Number of censorship tests run
  - name: blocked_tests
    type: INTEGER
    description: Number of tests resulting in blocked outcome
@bruin"""

import pandas as pd

# Bruin runtime import, with local fallback for VS Code
try:
    from staging import ooni
except ImportError:
    import assets.staging.ooni_staging as ooni


def materialize():
    # Load staging data
    df = ooni.materialize()

    # Aggregate by country, year, month
    fact_df = df.groupby(["country", "year", "month"]).agg(
        censorship_tests=("test_name", "count"),
        blocked_tests=("result", lambda x: (x == "blocked").sum())
    ).reset_index()

    print(f"Censorship tests fact rows: {len(fact_df)}")
    return fact_df
