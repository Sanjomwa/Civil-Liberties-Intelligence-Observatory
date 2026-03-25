/* @bruin
name: stg.google_transparency
type: sql
connection: duckdb-google
description: Cleaned Google Transparency takedown requests
owner: civil-liberties-pipeline
materialization:
    type: table
    strategy: create+replace
depends:
    - raw.google_transparency
columns:
    - name: country
      type: STRING
      description: Country issuing request
      checks:
          - name: not_null
    - name: period
      type: STRING
      description: Reporting period (YYYY-MM)
      checks:
          - name: not_null
    - name: request_count
      type: INTEGER
      description: Number of requests
      checks:
          - name: not_null
    - name: item_count
      type: INTEGER
      description: Number of items requested
    - name: extracted_at
      type: TIMESTAMP
      description: Pipeline extraction timestamp
custom_checks:
    - name: non_negative_counts
      description: Ensure request_count and item_count are non-negative
      query: "SELECT COUNT(*) FROM stg.google_transparency WHERE request_count < 0 OR item_count < 0"
      value: 0
@bruin */

WITH raw AS (
    SELECT * FROM raw.google_transparency
)
SELECT
    country,
    period,
    request_count,
    item_count,
    extracted_at
FROM raw
WHERE (period LIKE '%2024%' OR period LIKE '%2025%' OR period LIKE '%2026%')
  AND country IS NOT NULL;
