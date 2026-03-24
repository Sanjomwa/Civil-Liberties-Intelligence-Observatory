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
import random
from datetime import datetime, timedelta
from pathlib import Path

def materialize():
    # Generate synthetic records
    senders = ["Gov Agency", "Law Firm", "Communications Authority of Kenya"]
    recipients = ["Google", "Twitter", "Facebook", "TikTok", "YouTube"]
    reasons = ["Copyright", "Defamation", "National Security", "Other"]

    rows = []
    start_date = datetime(2024, 1, 1)
    for i in range(1, 101):  # 100 mock records
        date = start_date + timedelta(days=random.randint(0, 800))  # 2024–2026
        rows.append({
            "request_id": f"LUMEN-{i:03d}",
            "country": "KE",  # explicitly Kenya
            "sender": random.choice(senders),
            "recipient": random.choice(recipients),
            "date_submitted": date,
            "reason": random.choice(reasons),
            "extracted_at": datetime.now()
        })

    df = pd.DataFrame(rows)

    # Save to Parquet
    output_dir = Path("./data/lumen")
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_dir / "lumen.parquet", index=False)

    print(f"Lumen rows ingested (placeholder): {len(df)}")
    return df

# Register in DuckDB
con = duckdb.connect("duckdb-default.db")
con.execute("""
CREATE TABLE IF NOT EXISTS lumen_requests AS 
SELECT * FROM parquet_scan('./data/lumen/lumen.parquet')
""")
