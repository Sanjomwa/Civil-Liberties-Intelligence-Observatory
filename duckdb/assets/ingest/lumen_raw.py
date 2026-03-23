"""@bruin
name: raw.lumen_raw
type: python
image: python:3.11
connection: duckdb-default
description: |
  Placeholder ingestion for Lumen takedown requests (2024–2026).
  Simulates API JSON response until token access is granted.
  Converts to Parquet for consistency with other sources.

materialization:
  type: table
  strategy: append

columns:
  - name: request_id
    type: VARCHAR
    description: Unique takedown request ID
  - name: country
    type: VARCHAR
    description: Country of origin
  - name: sender
    type: VARCHAR
    description: Entity submitting the request
  - name: recipient
    type: VARCHAR
    description: Platform or service targeted
  - name: date_submitted
    type: TIMESTAMP
    description: Date the request was submitted
  - name: reason
    type: VARCHAR
    description: Reason for takedown (e.g. copyright, defamation)
  - name: extracted_at
    type: TIMESTAMP
    description: Timestamp when ingested
@bruin"""

import duckdb
import pandas as pd
from datetime import datetime


def materialize():
    # Placeholder JSON simulating API response
    mock_data = [
        {
            "request_id": "LUMEN-001",
            "country": "KE",
            "sender": "Gov Agency",
            "recipient": "Google",
            "date_submitted": "2024-05-12T00:00:00Z",
            "reason": "Defamation"
        },
        {
            "request_id": "LUMEN-002",
            "country": "KE",
            "sender": "Law Firm",
            "recipient": "Twitter",
            "date_submitted": "2025-09-20T00:00:00Z",
            "reason": "Copyright"
        }
    ]

    df = pd.DataFrame(mock_data)
    df["date_submitted"] = pd.to_datetime(df["date_submitted"])
    df["extracted_at"] = datetime.now()

    # Filter for 2024–2026
    df = df[df["date_submitted"].dt.year.between(2024, 2026)]

    # Save to Parquet
    df.to_parquet("./data/lumen/lumen.parquet", index=False)

    print(f"Lumen rows ingested (placeholder): {len(df)}")
    return df


con = duckdb.connect("duckdb-default.db")
con.execute("""
CREATE TABLE IF NOT EXISTS lumen_requests AS 
SELECT * FROM parquet_scan('./data/lumen/lumen.parquet')
""")
