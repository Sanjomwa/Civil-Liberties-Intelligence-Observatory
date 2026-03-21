"""@bruin
name: raw.ooni_raw
type: python
image: python:3.11
connection: duckdb-default
description: |
  Ingests OONI censorship measurement data from the OONI Explorer API.
  Fetches JSON measurement results filtered by country, ASN, date range, and test type.
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

import pandas as pd
import requests
import os
from datetime import datetime


def materialize():
    # Environment variables for filters
    start_date = os.environ.get("BRUIN_START_DATE")
    end_date = os.environ.get("BRUIN_END_DATE")
    bruin_vars = os.environ.get("BRUIN_VARS")

    # Example: parse filters from BRUIN_VARS JSON
    filters = {}
    if bruin_vars:
        import json
        filters = json.loads(bruin_vars)

    country = filters.get("country", "KE")  # default Kenya
    test_name = filters.get("test_name", "web_connectivity")

    # OONI Explorer API endpoint
    base_url = "https://api.ooni.org/api/v1/measurements"

    params = {
        "probe_cc": country,
        "test_name": test_name,
        "since": start_date,
        "until": end_date,
        "limit": 1000,  # adjust as needed
    }

    print(
        f"Fetching OONI data for {country}, test={test_name}, {start_date}–{end_date}")
    response = requests.get(base_url, params=params, timeout=300)
    response.raise_for_status()
    data = response.json()

    # Normalize JSON into DataFrame
    df = pd.json_normalize(data.get("results", []))
    df["extracted_at"] = datetime.now()

    print(f"Rows ingested: {len(df)}")
    return df
