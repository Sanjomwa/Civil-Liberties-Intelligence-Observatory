"""@bruin
name: stg.lumen
type: python
image: python:3.11
connection: duckdb-default
description: |
  Staging layer for Lumen takedown requests.
  Reads raw Parquet, normalizes schema, filters for 2024–2026.

materialization:
  type: table
  strategy: overwrite

columns:
  - name: request_id
    type: VARCHAR
  - name: country
    type: VARCHAR
  - name: sender
    type: VARCHAR
  - name: recipient
    type: VARCHAR
  - name: date_submitted
    type: TIMESTAMP
  - name: reason
    type: VARCHAR
  - name: extracted_at
    type: TIMESTAMP
@bruin"""

import duckdb


def materialize():
    con = duckdb.connect("duckdb-default.db")
    df = con.execute("""
        SELECT 
            request_id,
            country,
            sender,
            recipient,
            date_submitted,
            reason,
            extracted_at
        FROM parquet_scan('./data/lumen/lumen.parquet')
        WHERE strftime(date_submitted, '%Y') BETWEEN '2024' AND '2026'
    """).df()

    # Register staging table
    con.execute("CREATE TABLE IF NOT EXISTS stg_lumen AS SELECT * FROM df")
    return df
