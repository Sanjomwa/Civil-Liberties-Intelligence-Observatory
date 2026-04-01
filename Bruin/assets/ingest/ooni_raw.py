"""@bruin
name: raw.ooni_conflict_measurements
type: python
image: python:3.11
connection: duckdb-parquet
description: |
  Ingests OONI censorship measurement data from the public OONI S3 bucket.
  Syncs ONLY Kenya-specific JSONL files from June 2023–June 2025.
  Uses precise includes to avoid downloading any data from 2020–2022.

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

import subprocess
import glob
import os
import pandas as pd
from datetime import datetime
from pathlib import Path


# Bruin injects a context object with start_date and end_date


def materialize(context=None):
    base_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/ooni"
    parquet_out = f"{base_path}/ooni_measurements.parquet"

    Path(base_path).mkdir(parents=True, exist_ok=True)

    # Use Bruin context dates if provided, else default to project range
    since = context.start_date.strftime(
        "%Y-%m-%d") if context and context.start_date else "2023-06-01"
    until = context.end_date.strftime(
        "%Y-%m-%d") if context and context.end_date else "2025-06-30"

    # Guardrail: restrict to valid project window
    if since < "2023-06-01":
        since = "2023-06-01"
    if until > "2025-06-30":
        until = "2025-06-30"

    url = "https://api.ooni.io/api/v1/measurements"
    params = {
        "probe_cc": "KE",
        "since": since,
        "until": until,
        "limit": 500
    }

    all_rows = []
    next_url = url
    while next_url:
        resp = requests.get(
            next_url, params=params if next_url == url else None)
        resp.raise_for_status()
        data = resp.json()

        # Extract measurements
        results = data.get("results", [])
        for r in results:
            all_rows.append({
                "measurement_id": r.get("measurement_id"),
                "country": r.get("probe_cc"),
                "asn": r.get("probe_asn"),
                "test_name": r.get("test_name"),
                "input": r.get("input"),
                "start_time": r.get("start_time"),
                "status": "anomaly" if r.get("anomaly") else "ok",
                "probe_cc": r.get("probe_cc"),
                "probe_asn": r.get("probe_asn"),
                "extracted_at": datetime.now()
            })

        # Pagination
        next_url = data.get("metadata", {}).get("next_url")

    df = pd.DataFrame(all_rows)
    df.to_parquet(parquet_out, index=False, compression="snappy")

    print(f"✅ Parquet saved: {len(df):,} rows → {parquet_out}")
    return df
