"""@bruin
name: load.ooni_to_bigquery
type: python
image: python:3.11
connection: bigquery
description: |
  Loads the Parquet file (created in dev) into BigQuery.
  Use this in staging and prod environments.

materialization:
  type: table
  strategy: create+replace
  # BigQuery will create the table from the Parquet file

columns:
  - name: measurement_id
    type: STRING
  - name: country
    type: STRING
  - name: asn
    type: INTEGER
  - name: test_name
    type: STRING
  - name: input
    type: STRING
  - name: start_time
    type: TIMESTAMP
  - name: status
    type: STRING
  - name: probe_cc
    type: STRING
  - name: probe_asn
    type: INTEGER
  - name: extracted_at
    type: TIMESTAMP
@bruin"""

import pandas as pd
from datetime import datetime


def materialize():
    # Path to the Parquet file created in dev
    parquet_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/ooni/ooni_measurements.parquet"

    print(f"Loading Parquet file into BigQuery: {parquet_path}")

    df = pd.read_parquet(parquet_path)

    print(f"✅ Read {len(df):,} rows from Parquet file.")
    print(f"   Columns: {list(df.columns)}")

    # Add extracted_at if missing
    if "extracted_at" not in df.columns:
        df["extracted_at"] = datetime.now()

    print("Uploading to BigQuery...")

    # Bruin will automatically handle the materialization to the correct BigQuery table
    # based on environment (stg_ or prod_)

    return df