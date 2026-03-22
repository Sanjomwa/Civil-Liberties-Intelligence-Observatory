"""@bruin
name: dims.request_type
type: python
image: python:3.11
connection: duckdb-mart
description: |
  Dimension table for request types.
  Provides standardized request type values for joining with takedown and legal request fact tables.

materialization:
  type: table
  strategy: overwrite

columns:
  - name: request_type
    type: VARCHAR
    description: Standardized request type (e.g. court order, government request, DMCA, defamation)
@bruin"""

import pandas as pd

# Bruin runtime imports, with local fallbacks for VS Code
try:
    from staging import google_transparency, lumen
except ImportError:
    import assets.staging.google_transparency_staging as google_transparency
    import assets.staging.lumen_staging as lumen


def materialize():
    # Collect request_type values from both staging datasets
    google_df = google_transparency.materialize()[["request_type"]]
    lumen_df = lumen.materialize()[["request_type"]]

    # Concatenate and normalize
    request_types = pd.concat([google_df, lumen_df], ignore_index=True)
    request_types["request_type"] = request_types["request_type"].str.strip(
    ).str.lower()

    # Deduplicate
    request_types = request_types.drop_duplicates().reset_index(drop=True)

    print(f"Request type dimension rows: {len(request_types)}")
    return request_types
