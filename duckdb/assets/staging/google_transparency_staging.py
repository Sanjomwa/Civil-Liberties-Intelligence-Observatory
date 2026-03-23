"""@bruin
name: stg.google_transparency
type: python
image: python:3.11
connection: duckdb-default
description: |
  Staging layer for Google Transparency Report takedown requests.
  Reads raw Parquet, normalizes schema, filters for 2024–2026.

materialization:
  type: table
  strategy: overwrite

columns:
  - name: country
    type: VARCHAR
  - name: period
    type: VARCHAR
  - name: request_count
    type: INTEGER
  - name: item_count
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
            period,
            request_count,
            item_count,
            extracted_at
        FROM parquet_scan('./data/google/google_transparency.parquet')
        WHERE period LIKE '%2024%' OR period LIKE '%2025%' OR period LIKE '%2026%'
    """).df()

    # Register staging table
    con.execute(
        "CREATE TABLE IF NOT EXISTS stg_google_transparency AS SELECT * FROM df")
    return df
