/* @bruin
name: fact.takedown_requests
type: sql
connection: duckdb-mart
description: Fact table for Google Transparency takedown requests
owner: civil-liberties-pipeline
materialization:
    type: table
    strategy: overwrite
depends:
    - stg.google_transparency
    - dims.country
columns:
    - name: country
      type: STRING
      description: Standardized country name
      checks: [not_null]
    - name: period
      type: STRING
      description: Reporting period (YYYY-MM)
      checks: [not_null]
    - name: request_count
      type: INTEGER
      description: Number of requests
      checks: [non_negative]
    - name: item_count
      type: INTEGER
      description: Number of items requested
      checks: [non_negative]
    - name: extracted_at
      type: TIMESTAMP
      description: Pipeline extraction timestamp
@bruin */

SELECT
    c.country,
    g.period,
    g.request_count,
    g.item_count,
    g.extracted_at
FROM stg.google_transparency g
JOIN dims.country c
  ON LOWER(TRIM(g.country)) = LOWER(TRIM(c.country));
