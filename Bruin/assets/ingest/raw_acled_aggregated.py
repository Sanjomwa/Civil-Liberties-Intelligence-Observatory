"""@bruin
name: raw.acled_conflict_events
type: python
image: python:3.11
connection: duckdb-parquet
description: Ingests ACLED aggregated conflict events CSV into raw table and exports as Parquet.
owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace

columns:
  - name: event_id
    type: STRING
  - name: event_date
    type: DATE
  - name: country
    type: STRING
  - name: event_type
    type: STRING
  - name: fatalities
    type: INTEGER
  - name: extracted_at
    type: TIMESTAMP
@bruin"""

import pandas as pd
from datetime import datetime
from pathlib import Path


def materialize():
    base_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/acled"
    csv_file = Path(base_path) / "Africa_aggregated_data_up_to_week_of-2026-03-14.csv"
    parquet_out = Path(base_path) / "acled_conflict_events.parquet"

    print(f"📂 Reading ACLED CSV: {csv_file.name}")

    df = pd.read_csv(csv_file)

    df = df.rename(columns={
        "EVENT_ID_CNTY": "event_id",
        "EVENT_DATE": "event_date",
        "COUNTRY": "country",
        "EVENT_TYPE": "event_type",
        "FATALITIES": "fatalities"
    })

    df["extracted_at"] = datetime.now()

    df.to_parquet(parquet_out, index=False, compression="snappy")

    print(f"✅ Ingested {len(df):,} ACLED conflict events")
    return df
