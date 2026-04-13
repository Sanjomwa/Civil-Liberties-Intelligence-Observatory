"""@bruin
tags:
  - raw_dev
  - dataset_acled_conflict_events
name: raw.acled_conflict_events
type: python
image: python:3.12
connection: duckdb-parquet
description: Ingests ACLED aggregated conflict events CSV into raw table and exports as Parquet.
owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace

columns:
  - name: week
    type: STRING
    description: Week of the event
  - name: region
    type: STRING
    description: Region of the event
  - name: country
    type: STRING
    description: Country of the event
  - name: admin1
    type: STRING
    description: First administrative division
  - name: event_type
    type: STRING
    description: Type of conflict event
  - name: sub_event_type
    type: STRING
    description: Sub-type of conflict event
  - name: events
    type: INTEGER
    description: Number of events
  - name: fatalities
    type: INTEGER
    description: Number of fatalities
  - name: population_exposure
    type: INTEGER
    description: Population exposure
  - name: disorder_type
    type: STRING
    description: Disorder type classification
  - name: id
    type: STRING
    description: ACLED record identifier
  - name: centroid_latitude
    type: FLOAT
    description: Latitude of centroid
  - name: centroid_longitude
    type: FLOAT
    description: Longitude of centroid
  - name: extracted_at
    type: TIMESTAMP
    description: Pipeline extraction timestamp
@bruin"""

import os
import pandas as pd
from datetime import datetime
from pathlib import Path

import os


def resolve_env(fallback: str = "dev") -> str:
    for k in ("BRUIN_ENV", "BRUIN_ENVIRONMENT", "BRUIN_PIPELINE_ENVIRONMENT"):
        v = os.getenv(k)
        if v and v.strip():
            return v.strip().lower()
    return fallback


def require_dev(env: str) -> None:
    if env != "dev":
        raise ValueError(f"This raw asset is dev-only. Got ENV={env!r}.")


ENV = resolve_env(fallback="dev")
require_dev(ENV)


def materialize():
    base_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/acled"
    csv_file = Path(base_path) / \
        "Africa_aggregated_data_up_to_week_of-2026-03-14.csv"
    parquet_out = Path(base_path) / "acled_conflict_events.parquet"

    print(f"📂 Reading ACLED CSV: {csv_file.name}")

    df = pd.read_csv(csv_file)
    df = df.rename(columns={
        "WEEK": "week",
        "REGION": "region",
        "COUNTRY": "country",
        "ADMIN1": "admin1",
        "EVENT_TYPE": "event_type",
        "SUB_EVENT_TYPE": "sub_event_type",
        "EVENTS": "events",
        "FATALITIES": "fatalities",
        "POPULATION_EXPOSURE": "population_exposure",
        "DISORDER_TYPE": "disorder_type",
        "ID": "id",
        "CENTROID_LATITUDE": "centroid_latitude",
        "CENTROID_LONGITUDE": "centroid_longitude"
    })

    df["extracted_at"] = datetime.now()
    df.to_parquet(parquet_out, index=False, compression="snappy")

    print(f"✅ Ingested {len(df):,} ACLED conflict events")
    return df
