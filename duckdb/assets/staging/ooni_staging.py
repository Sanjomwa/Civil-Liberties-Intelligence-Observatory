"""@bruin
name: stg.ooni
type: python
image: python:3.11
connection: duckdb-default
description: |
  Staging layer for OONI censorship measurements.
  Reads raw Parquet, normalizes schema, filters for 2024–2026.

materialization:
  type: table
  strategy: overwrite

columns:
  - name: measurement_id
    type: VARCHAR
  - name: country
    type: VARCHAR
  - name: test_name
    type: VARCHAR
  - name: input
    type: VARCHAR
  - name: start_time
    type: TIMESTAMP
  - name: status
    type: VARCHAR
  - name: probe_cc
    type: VARCHAR
  - name: probe_asn
    type: INTEGER
  - name: extracted_at
    type: TIMESTAMP
@bruin"""

import duckdb


def materialize():
    con = duckdb.connect("duckdb-default.db")
    df = con.execute("""
        SELECT 
            measurement_id,
            probe_cc AS country,
            test_name,
            input,
            start_time,
            status,
            probe_cc,
            probe_asn,
            extracted_at
        FROM parquet_scan('./data/ooni/ooni.parquet')
        WHERE strftime(start_time, '%Y') BETWEEN '2024' AND '2026'
    """).df()

    # Register staging table
    con.execute("CREATE TABLE IF NOT EXISTS stg_ooni AS SELECT * FROM df")
    return df
