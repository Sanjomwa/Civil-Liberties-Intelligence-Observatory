"""@bruin
name: dims.platform
type: python
image: python:3.11
connection: duckdb-mart
description: |
  Dimension table for platforms/recipients targeted in Lumen requests.
  Provides standardized platform values for joining with legal requests fact table.

materialization:
  type: table
  strategy: overwrite

columns:
  - name: platform
    type: VARCHAR
    description: Standardized platform or recipient (e.g. YouTube, Google, Facebook, Twitter)
@bruin"""

import pandas as pd

# Bruin runtime import, with local fallback for VS Code
try:
    from staging import lumen
except ImportError:
    import assets.staging.lumen_staging as lumen


def materialize():
    # Load staging data
    df = lumen.materialize()[["recipient"]]

    # Normalize recipient/platform values
    df["platform"] = df["recipient"].str.strip().str.title()

    # Deduplicate
    platforms = df[["platform"]].drop_duplicates().reset_index(drop=True)

    print(f"Platform dimension rows: {len(platforms)}")
    return platforms
