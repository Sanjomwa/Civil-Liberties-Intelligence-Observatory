"""@bruin
name: dims.event_type
type: python
image: python:3.11
connection: duckdb-mart
description: |
  Dimension table for ACLED event types.
  Provides standardized event type values for joining with conflict events fact table.

materialization:
  type: table
  strategy: overwrite

columns:
  - name: event_type
    type: VARCHAR
    description: Standardized event type (e.g. battles, protests, violence against civilians)
@bruin"""

import pandas as pd

# Bruin runtime import, with local fallback for VS Code
try:
    from staging import acled
except ImportError:
    import assets.staging.acled_staging as acled


def materialize():
    # Load staging data
    df = acled.materialize()[["event_type"]]

    # Normalize event_type values
    df["event_type"] = df["event_type"].str.strip().str.lower()

    # Deduplicate
    event_types = df.drop_duplicates().reset_index(drop=True)

    print(f"Event type dimension rows: {len(event_types)}")
    return event_types
