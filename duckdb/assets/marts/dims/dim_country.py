"""@bruin
name: dims.country
type: python
image: python:3.11
connection: duckdb-mart
description: |
  Dimension table for countries.
  Provides standardized country names for joining across fact tables.

materialization:
  type: table
  strategy: overwrite

columns:
  - name: country
    type: VARCHAR
    description: Country name (standardized)
@bruin"""

import pandas as pd

# Bruin runtime imports with local fallbacks
try:
    from staging import acled, ooni, google_transparency, lumen
except ImportError:
    import assets.staging.acled_staging as acled
    import assets.staging.ooni_staging as ooni
    import assets.staging.google_transparency_staging as google_transparency
    import assets.staging.lumen_staging as lumen


def materialize():
    # Collect country values from all staging datasets
    acled_df = acled.materialize()[["country"]]
    ooni_df = ooni.materialize()[["country"]]
    google_df = google_transparency.materialize()[["country"]]
    lumen_df = lumen.materialize()[["country"]]

    # Concatenate and deduplicate
    countries = pd.concat([acled_df, ooni_df, google_df,
                          lumen_df], ignore_index=True)
    countries["country"] = countries["country"].str.strip().str.title()
    countries = countries.drop_duplicates().reset_index(drop=True)

    print(f"Country dimension rows: {len(countries)}")
    return countries
