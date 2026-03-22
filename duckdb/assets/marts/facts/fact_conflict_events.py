"""@bruin
name: facts.conflict_events
type: python
image: python:3.11
connection: duckdb-mart
description: |
  Fact table for conflict events from ACLED staging.
  Aggregates fatalities and event counts by country, year, and month.

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
  - name: conflict_events
    type: INTEGER
    description: Number of conflict events
  - name: fatalities
    type: INTEGER
    description: Number of reported fatalities
@bruin"""

import pandas as pd

# Bruin runtime import, with local fallback for VS Code
try:
    from staging import acled
except ImportError:
    import assets.staging.acled_staging as acled


def materialize():
    # Load staging data
    df = acled.materialize()

    # Aggregate by country, year, month
    fact_df = df.groupby(["country", "year", "month"]).agg(
        conflict_events=("event_count", "sum"),
        fatalities=("fatalities", "sum")
    ).reset_index()

    print(f"Conflict events fact rows: {len(fact_df)}")
    return fact_df
