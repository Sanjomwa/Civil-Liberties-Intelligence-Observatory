"""@bruin
name: raw.ooni_conflict_measurements
type: python
image: python:3.11
connection: duckdb-parquet
description: |
  Ingests OONI censorship measurement data via the OONI Measurement API.
  Queries Kenya-specific records (June 2023–June 2025) and converts them to Parquet.
  Returns a Pandas DataFrame for Bruin to create/replace into DuckDB.

materialization:
  type: table
  strategy: create+replace

packages:
  - pandas
  - requests

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

import requests
import pandas as pd
from datetime import datetime
from pathlib import Path

def materialize():
    base_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/ooni"
    parquet_out = f"{base_path}/ooni_measurements.parquet"
    Path(base_path).mkdir(parents=True, exist_ok=True)

    # API parameters
    url = "https://api.ooni.io/api/v1/measurements"
    params = {
        "probe_cc": "KE",
        "since": "2023-06-01",
        "until": "2025-06-30",
        "limit": 500  # API returns up to 500 per page
    }

    all_rows = []
    next_url = url
    while next_url:
        resp = requests.get(next_url, params=params if next_url == url else None)
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
                "status": r.get("anomaly"),  # simplified status
                "probe_cc": r.get("probe_cc"),
                "probe_asn": r.get("probe_asn"),
                "extracted_at": datetime.now()
            })

        # Pagination
        next_url = data.get("metadata", {}).get("next_url")

    df = pd.DataFrame(all_rows)
    df.to_parquet(parquet_out, index=False, compression="snappy")

    print(f"✅ OONI rows ingested: {len(df)}")
    return df
