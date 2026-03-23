"""@bruin
name: raw.ooni_raw
type: python
image: python:3.11
connection: duckdb-default
description: |
  Ingests OONI censorship measurement data from the public OONI S3 bucket.
  Syncs Kenya-specific JSONL files (2024–2026) and converts them to Parquet.
  Returns a Pandas DataFrame for Bruin to append into DuckDB.

materialization:
  type: table
  strategy: append

columns:
  - name: measurement_id
    type: VARCHAR
    description: Unique OONI measurement ID
  - name: country
    type: VARCHAR
    description: Country code (ISO two-letter)
  - name: asn
    type: INTEGER
    description: Autonomous System Number (network identifier)
  - name: test_name
    type: VARCHAR
    description: OONI Probe test type (e.g. web_connectivity, whatsapp)
  - name: input
    type: VARCHAR
    description: Domain or URL tested
  - name: start_time
    type: TIMESTAMP
    description: Measurement start time (UTC)
  - name: status
    type: VARCHAR
    description: Result status (ok, anomaly, confirmed, failure)
  - name: probe_cc
    type: VARCHAR
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
    # Step 1: Sync Kenya data from OONI S3 (2024–2026 only)
    # This command is incremental: only new files are downloaded
    sync_cmd = [
        "aws", "s3", "--no-sign-request", "sync",
        "s3://ooni-data-eu-fra/raw/", "./data/ooni",
        "--exclude", "*", "--include", "*/KE/*.jsonl.gz"
    ]
    subprocess.run(sync_cmd, check=True)

    # Step 2: Read all JSONL files
    files = glob.glob("./data/ooni/**/*.jsonl.gz", recursive=True)
    rows = []
    for file in files:
        # Filter by year range (2024–2026) based on filename
        if any(year in file for year in ["2024", "2025", "2026"]):
            with gzip.open(file, "rt") as f:
                for line in f:
                    rows.append(json.loads(line))

    df = pd.DataFrame(rows)
    df["extracted_at"] = datetime.now()

    # Step 3: Save to Parquet (schema preserved)
    df.to_parquet("./data/ooni/ooni.parquet", index=False)

    print(f"OONI rows ingested: {len(df)}")
    return df
