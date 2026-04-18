"""
@bruin
tags:
  - raw_dev
  - dataset_lumen_requests
name: raw.lumen_requests
type: python
image: python:3.12
connection: duckdb-parquet

description:
  Deterministic mock Lumen dataset with SAFE timestamp encoding (micros INT64).

materialization:
  type: table
  strategy: create+replace
"""

import os
import pandas as pd
import random
from datetime import datetime, timedelta
from pathlib import Path


def resolve_env(fallback: str = "dev") -> str:
    for k in ("BRUIN_ENV", "BRUIN_ENVIRONMENT", "BRUIN_PIPELINE_ENVIRONMENT"):
        v = os.getenv(k)
        if v:
            return v.strip().lower()
    return fallback


def require_dev(env: str) -> None:
    if env != "dev":
        raise ValueError(f"Dev-only asset. Got ENV={env}")


ENV = resolve_env()
require_dev(ENV)


def materialize():
    base_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/lumen"
    Path(base_path).mkdir(parents=True, exist_ok=True)
    parquet_out = Path(base_path) / "lumen_requests.parquet"

    senders = ["Gov Agency", "Law Firm", "Communications Authority of Kenya"]
    recipients = ["Google", "Twitter", "Facebook", "TikTok", "YouTube"]
    reasons = ["Copyright", "Defamation", "National Security", "Other"]

    rows = []

    start_date = datetime(2023, 6, 1)
    end_date = datetime(2025, 6, 30)
    total_days = (end_date - start_date).days

    for i in range(1, 501):
        dt = start_date + timedelta(days=random.randint(0, total_days))

        # 🔥 FIX: deterministic micros epoch
        timestamp_micros = int(dt.timestamp() * 1_000_000)

        rows.append({
            "request_id": f"LUMEN-{i:04d}",
            "country": "KE",
            "sender": random.choice(senders),
            "recipient": random.choice(recipients),

            # 🔥 CRITICAL FIX: store INT64 micros, not TIMESTAMP object
            "date_submitted": timestamp_micros,

            "period": f"{dt.year}-{'06' if dt.month <= 6 else '12'}",
            "half_year_label": f"{'Jan-Jun' if dt.month <= 6 else 'Jul-Dec'} {dt.year}",
            "reason": random.choice(reasons),

            "request_count": 1,
            "item_count": 1,

            # keep audit field stable
            "extracted_at": datetime.utcnow()
        })

    df = pd.DataFrame(rows)

    df.to_parquet(parquet_out, index=False, compression="snappy")

    print(f"✅ Generated {len(df)} Lumen rows (micros-safe)")
    return df
