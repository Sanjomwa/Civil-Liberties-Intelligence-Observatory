"""@bruin
name: raw.lumen_requests
type: python
image: python:3.11
connection: duckdb-parquet
description: |
  Generates mock Lumen takedown requests (Jun 2023–Jun 2025) until real API access is available.

materialization:
  type: table
  strategy: create+replace

columns:
  - name: request_id
    type: VARCHAR
  - name: country
    type: VARCHAR
  - name: sender
    type: VARCHAR
  - name: recipient
    type: VARCHAR
  - name: date_submitted
    type: TIMESTAMP
  - name: period
    type: VARCHAR
  - name: half_year_label
    type: VARCHAR
  - name: reason
    type: VARCHAR
  - name: request_count
    type: INTEGER
  - name: item_count
    type: INTEGER
  - name: extracted_at
    type: TIMESTAMP
@bruin"""

import pandas as pd
import random
from datetime import datetime, timedelta
from pathlib import Path


def materialize():
    base_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/lumen"
    Path(base_path).mkdir(parents=True, exist_ok=True)
    parquet_out = Path(base_path) / "lumen_requests.parquet"

    print("Generating mock Lumen takedown data...")

    # Mock data parameters
    senders = ["Gov Agency", "Law Firm", "Communications Authority of Kenya"]
    recipients = ["Google", "Twitter", "Facebook", "TikTok", "YouTube"]
    reasons = ["Copyright", "Defamation", "National Security", "Other"]

    rows = []
    start_date = datetime(2023, 6, 1)
    end_date = datetime(2025, 6, 30)
    total_days = (end_date - start_date).days

    for i in range(1, 501):  # increased to 500 for better coverage
        date = start_date + timedelta(days=random.randint(0, total_days))
        year = date.year
        month = date.month
        period = f"{year}-06" if month <= 6 else f"{year}-12"
        half_year_label = f"Jan-Jun {year}" if month <= 6 else f"Jul-Dec {year}"

        rows.append({
            "request_id": f"LUMEN-{i:04d}",
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
    df.to_parquet(parquet_out, index=False, compression="snappy")

    print(f"✅ Generated {len(df):,} mock Lumen rows")
    return df
