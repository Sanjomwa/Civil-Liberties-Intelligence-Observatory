"""@bruin
name: stg.acled
type: python
image: python:3.11
connection: duckdb-default
description: |
  Staging layer for ACLED aggregated conflict data (Africa).
  Reads raw Parquet, normalizes schema, filters for 2024–2026.

materialization:
  type: table
  strategy: overwrite

columns:
  - name: country
    type: VARCHAR
  - name: admin1
    type: VARCHAR
  - name: event_type
    type: VARCHAR
  - name: fatalities
    type: INTEGER
  - name: event_count
    type: INTEGER
  - name: year
    type: INTEGER
  - name: month
    type: INTEGER
  - name: extracted_at
    type: TIMESTAMP
@bruin"""

import duckdb


def materialize():
    con = duckdb.connect("duckdb-default.db")
    df = con.execute("""
        SELECT 
            country,
            admin1,
            event_type,
            fatalities,
            event_count,
            year,
            month,
            extracted_at
        FROM parquet_scan('./data/acled/acled.parquet')
        WHERE year BETWEEN 2024 AND 2026
    """).df()

    # Register staging table
    con.execute("CREATE TABLE IF NOT EXISTS stg_acled AS SELECT * FROM df")
    return df
