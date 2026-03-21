"""@bruin
name: raw.lumen_raw
type: python
image: python:3.11
connection: duckdb-default
description: |
  Ingests Lumen takedown request data via the Lumen API.
  Requires an API token for authentication (to be provided later).
  Returns a Pandas DataFrame for Bruin to append into DuckDB.

materialization:
  type: table
  strategy: append

columns:
  - name: request_id
    type: VARCHAR
    description: Unique takedown request ID
  - name: date_submitted
    type: DATE
    description: Date the request was submitted
  - name: sender
    type: VARCHAR
    description: Entity submitting the request
  - name: recipient
    type: VARCHAR
    description: Platform or service receiving the request
  - name: country
    type: VARCHAR
    description: Country of origin
  - name: type
    type: VARCHAR
    description: Type of request (copyright, defamation, etc.)
  - name: content_url
    type: VARCHAR
    description: URL of content targeted
  - name: notes
    type: VARCHAR
    description: Additional notes or metadata
  - name: extracted_at
    type: TIMESTAMP
    description: Timestamp when ingested
@bruin"""

import pandas as pd
import requests
import os
from datetime import datetime


def materialize():
    # Placeholder for token – set this once you receive it
    lumen_token = os.environ.get("LUMEN_API_TOKEN")
    if not lumen_token:
        raise ValueError(
            "Missing LUMEN_API_TOKEN. Please set it in environment variables.")

    headers = {
        "Authorization": f"Bearer {lumen_token}",
        "Accept": "application/json"
    }

    # Example endpoint – replace with actual Lumen API URL
    url = "https://api.lumendatabase.org/takedowns?start_date=2024-01-01&end_date=2026-12-31"

    print(f"Fetching Lumen takedown data from {url}")
    response = requests.get(url, headers=headers, timeout=300)
    response.raise_for_status()

    data = response.json()

    # Normalize JSON into DataFrame
    df = pd.json_normalize(data.get("results", []))
    df.columns = df.columns.str.lower().str.replace(" ", "_")
    df["extracted_at"] = datetime.now()

    print(f"Rows ingested: {len(df)}")
    return df
