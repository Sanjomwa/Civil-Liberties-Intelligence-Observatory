"""@bruin
name: raw.acled_conflict_events
type: python
image: python:3.11
connection: duckdb-parquet
description: Ingest ACLED aggregated conflict events CSV into raw table and export as Parquet
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

import os
import pandas as pd
from datetime import datetime


def materialize():
    base_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/acled/"
    csv_file = os.path.join(
        base_path, "Africa_aggregated_data_up_to_week_of-2026-03-14.csv")
    parquet_out = os.path.join(base_path, "acled_conflict_events.parquet")

    # Read CSV into Pandas
    df = pd.read_csv(csv_file)

    # Normalize column names
    df = df.rename(columns={
        "EVENT_ID_CNTY": "event_id",
        "EVENT_DATE": "event_date",
        "COUNTRY": "country",
        "EVENT_TYPE": "event_type",
        "FATALITIES": "fatalities"
    })

    df["extracted_at"] = datetime.now()

    df.to_parquet(parquet_out, index=False)

    print(f"✅ Ingested {len(df)} ACLED conflict events")
    return df
