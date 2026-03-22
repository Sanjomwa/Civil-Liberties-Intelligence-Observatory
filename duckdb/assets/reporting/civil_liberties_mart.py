"""@bruin
name: reporting.civil_liberties
type: python
image: python:3.11
connection: duckdb-reporting
description: |
  Unified reporting mart combining conflict, censorship, takedown, and legal requests.
  Aggregates by country, year, and month for dashboard analysis.

materialization:
  type: table
  strategy: overwrite

columns:
  - name: country
    type: VARCHAR
    description: Country key
  - name: year
    type: INTEGER
    description: Year of aggregation
  - name: month
    type: INTEGER
    description: Month of aggregation
  - name: conflict_events
    type: INTEGER
    description: Number of conflict events (ACLED)
  - name: fatalities
    type: INTEGER
    description: Reported fatalities (ACLED)
  - name: censorship_tests
    type: INTEGER
    description: Number of censorship tests (OONI)
  - name: blocked_tests
    type: INTEGER
    description: Number of blocked outcomes (OONI)
  - name: takedown_requests
    type: INTEGER
    description: Number of takedown requests (Google Transparency)
  - name: items_requested
    type: INTEGER
    description: Items requested for removal (Google Transparency)
  - name: legal_requests
    type: INTEGER
    description: Number of legal requests (Lumen)
@bruin"""

import pandas as pd

# Bruin runtime imports with local fallbacks
try:
    from facts import conflict_events, censorship_tests, takedown_requests, legal_requests
    from dims import country
except ImportError:
    import assets.marts.facts.fact_conflict_events as conflict_events
    import assets.marts.facts.fact_censorship_tests as censorship_tests
    import assets.marts.facts.fact_takedown_requests as takedown_requests
    import assets.marts.facts.fact_legal_requests as legal_requests
    import assets.marts.dims.dim_country as country


def materialize():
    # Load fact tables
    conflict_df = conflict_events.materialize()
    censorship_df = censorship_tests.materialize()
    takedown_df = takedown_requests.materialize()
    legal_df = legal_requests.materialize()

    # Merge all facts on country + year + month
    mart = conflict_df \
        .merge(censorship_df, on=["country", "year", "month"], how="outer") \
        .merge(takedown_df, on=["country", "year", "month"], how="outer") \
        .merge(legal_df, on=["country", "year", "month"], how="outer")

    # Fill missing values with 0
    mart = mart.fillna(0)

    # Join with country dimension for standardized names
    country_dim = country.materialize()
    mart = mart.merge(country_dim, on="country", how="left")

    print(f"Civil Liberties reporting mart rows: {len(mart)}")
    return mart
