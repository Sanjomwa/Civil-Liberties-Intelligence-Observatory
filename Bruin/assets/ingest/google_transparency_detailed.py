"""@bruin
tags:
  - raw_dev
  - dataset_google_transparency_detailed
name: raw.google_transparency_detailed
type: python
image: python:3.12
connection: duckdb-parquet
description: Ingests Google Transparency detailed removal requests CSV and exports as Parquet.

materialization:
  type: table
  strategy: create+replace

columns:
  - name: period_ending
    type: STRING
    description: Period ending date
  - name: country_region
    type: STRING
    description: Country or region issuing request
  - name: cldr_territory_code
    type: STRING
    description: CLDR territory code
  - name: product
    type: STRING
    description: Google product targeted
  - name: reason
    type: STRING
    description: Reason for takedown
  - name: total
    type: INTEGER
    description: Total requests
  - name: extracted_at
    type: TIMESTAMP
    description: Pipeline extraction timestamp
@bruin"""

import pandas as pd
from datetime import datetime
from pathlib import Path

from _env import resolve_env, require_dev
ENV = resolve_env(fallback="dev")
require_dev(ENV)

def materialize():
    base_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/google"
    csv_file = Path(base_path) / "google-government-detailed-removal-requests.csv"
    parquet_out = Path(base_path) / "google_transparency_detailed.parquet"

    print(f"📂 Reading Google detailed CSV: {csv_file.name}")

    df = pd.read_csv(csv_file)
    df = df.rename(columns={
        "Period Ending": "period_ending",
        "Country/Region": "country_region",
        "CLDR Territory Code": "cldr_territory_code",
        "Product": "product",
        "Reason": "reason",
        "Total": "total"
    })

    df["extracted_at"] = datetime.now()
    df.to_parquet(parquet_out, index=False, compression="snappy")

    print(f"✅ Ingested {len(df):,} rows → google_transparency_detailed")
    return df
