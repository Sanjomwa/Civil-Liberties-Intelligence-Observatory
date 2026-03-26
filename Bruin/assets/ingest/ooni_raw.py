"""@bruin
name: raw.ooni_conflict_measurements
type: python
image: python:3.11
connection: duckdb-parquet
description: |
  Ingests OONI censorship measurement data from the public OONI S3 bucket.
  Syncs Kenya-specific JSONL files (June 2023–June 2025) and converts them to Parquet.
  Returns a Pandas DataFrame for Bruin to create/replace into DuckDB.

materialization:
  type: table
  strategy: create+replace

packages:
  - pandas

columns:
  - name: measurement_id
    type: STRING
    description: Unique OONI measurement ID
  - name: country
    type: STRING
    description: Country code (ISO two-letter)
  - name: asn
    type: INTEGER
    description: Autonomous System Number (network identifier)
  - name: test_name
    type: STRING
    description: OONI Probe test type (e.g. web_connectivity, whatsapp)
  - name: input
    type: STRING
    description: Domain or URL tested
  - name: start_time
    type: TIMESTAMP
    description: Measurement start time (UTC)
  - name: status
    type: STRING
    description: Result status (ok, anomaly, confirmed, failure)
  - name: probe_cc
    type: STRING
    description: Country code of probe
  - name: probe_asn
    type: INTEGER
    description: ASN of probe
  - name: extracted_at
    type: TIMESTAMP
    description: Timestamp when ingested
@bruin"""

import gzip
import json
import glob
import subprocess
import pandas as pd
from datetime import datetime


def materialize():
    base_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/ooni"
    parquet_out = f"{base_path}/ooni_measurements.parquet"

    # Step 1: Sync Kenya data from OONI S3
    sync_cmd = [
        "aws", "s3", "--no-sign-request", "sync",
        "s3://ooni-data-eu-fra/raw/", base_path,
        "--exclude", "*", "--include", "*/KE/*.jsonl.gz"
    ]
    subprocess.run(sync_cmd, check=True)

    # Step 2: Read JSONL files
    files = glob.glob(f"{base_path}/**/*.jsonl.gz", recursive=True)
    rows = []
    for file in files:
        with gzip.open(file, "rt") as f:
            for line in f:
                record = json.loads(line)
                # Parse start_time and filter by June 2023 – June 2025
                try:
                    ts = pd.to_datetime(record.get("start_time"))
                    if ts >= pd.Timestamp("2023-06-01") and ts <= pd.Timestamp("2025-06-30"):
                        rows.append(record)
                except Exception:
                    continue

    df = pd.DataFrame(rows)
    df["extracted_at"] = datetime.now()

    # Step 3: Save to Parquet
    df.to_parquet(parquet_out, index=False)

    print(f"✅ OONI rows ingested: {len(df)}")
    return df
