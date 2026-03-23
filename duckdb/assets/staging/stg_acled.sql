/* @bruin
name: stg.acled
type: sql
connection: duckdb-acled
description: Cleaned ACLED conflict events
owner: civil-liberties-pipeline
materialization:
    type: table
    strategy: overwrite
depends:
    - raw.acled_aggregated
columns:
    - name: country
      type: STRING
      description: Country of event
      checks:
          - name: not_null
    - name: admin1
      type: STRING
      description: First-level administrative division
    - name: event_type
      type: STRING
      description: Type of conflict event
      checks:
          - name: not_null
    - name: fatalities
      type: INTEGER
      description: Number of fatalities
      checks:
          - name: non_negative
    - name: event_count
      type: INTEGER
      description: Number of events aggregated
      checks:
          - name: non_negative
    - name: year
      type: INTEGER
      description: Event year
      checks:
          - name: not_null
    - name: month
      type: INTEGER
      description: Event month
    - name: extracted_at
      type: TIMESTAMP
      description: Pipeline extraction timestamp
@bruin */

WITH raw AS (
    SELECT * FROM raw.acled_aggregated
)
SELECT
    country,
    admin1,
    event_type,
    fatalities,
    event_count,
    year,
    month,
    extracted_at
FROM raw
WHERE year BETWEEN 2024 AND 2026
  AND country IS NOT NULL;
