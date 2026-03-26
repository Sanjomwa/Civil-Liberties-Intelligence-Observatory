"""@bruin
name: raw.lumen_requests
type: python
image: python:3.11
connection: duckdb-parquet
description: |
  Placeholder ingestion for Lumen takedown requests (Jun 2023–Jun 2025).
  Generates mock JSON-like records until API token access is granted.
  Converts to Parquet for consistency with Google ingests.

materialization:
  type: table
  strategy: create+replace   # overwrite instead of append

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
  - name: period
    type: VARCHAR
    description: Reporting period (YYYY-MM)
  - name: half_year_label
    type: VARCHAR
    description: Human-readable half-year (e.g. Jan-Jun 2024)
  - name: reason
    type: VARCHAR
    description: Reason for takedown
  - name: request_count
    type: INTEGER
    description: Always 1 for mock records
  - name: item_count
    type: INTEGER
    description: Always 1 for mock records
  - name: extracted_at
    type: TIMESTAMP
    description: Timestamp when ingested
@bruin"""

import pandas as pd
import random
from datetime import datetime, timedelta
from pathlib import Path


def materialize():
    senders = ["Gov Agency", "Law Firm", "Communications Authority of Kenya"]
    recipients = ["Google", "Twitter", "Facebook", "TikTok", "YouTube"]
    reasons = ["Copyright", "Defamation", "National Security", "Other"]

    rows = []
    start_date = datetime(2023, 6, 1)
    end_date = datetime(2025, 6, 30)
    total_days = (end_date - start_date).days

    for i in range(1, 101):
        date = start_date + timedelta(days=random.randint(0, total_days))
        year = date.year
        month = date.month
        if month <= 6:
            period = f"{year}-06"
            half_year_label = f"Jan-Jun {year}"
        else:
            period = f"{year}-12"
            half_year_label = f"Jul-Dec {year}"

        rows.append({
            "request_id": f"LUMEN-{i:03d}",
            "country": "KE",
            "sender": random.choice(senders),
            "recipient": random.choice(recipients),
            "date_submitted": date,
            "period": period,
            "half_year_label": half_year_label,
            "reason": random.choice(reasons),
            "request_count": 1,
            "item_count": 1,
            "extracted_at": datetime.now()
        })

    df = pd.DataFrame(rows)

    # Save to Parquet so staging can pick it up
    output_dir = Path(
        "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/lumen")
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_dir / "lumen_requests.parquet", index=False)

    print(f"Lumen rows ingested (placeholder): {len(df)}")
    return df
