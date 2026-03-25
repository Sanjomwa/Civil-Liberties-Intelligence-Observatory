/* @bruin
name: fact.takedown_requests
type: duckdb.sql          # ← used only in 'dev' environment
connection: duckdb-mart

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Fact table for Google Transparency takedown requests
owner: civil-liberties-pipeline

materialization:
    type: table
    strategy: create+replace

depends:
    - stg.google_transparency
    - dims.country
    - dims.platform
    - dims.reasons
    - dims.periods

columns:
    - name: country
      type: STRING
      description: Standardized country name
      checks:
        - name: not_null
    - name: period
      type: STRING
      description: Reporting period (YYYY-MM)
      checks:
        - name: not_null
    - name: half_year_label
      type: STRING
      description: Human-readable half-year (e.g. Jan-Jun 2023)
    - name: product
      type: STRING
      description: Platform targeted
    - name: reason
      type: STRING
      description: Legal or policy grounds
    - name: request_count
      type: INTEGER
      description: Number of requests
      checks:
        - name: non_negative
    - name: item_count
      type: INTEGER
      description: Number of items requested
      checks:
        - name: non_negative
    - name: extracted_at
      type: TIMESTAMP
      description: Pipeline extraction timestamp

custom_checks:
    - name: valid_period_range
      description: Ensure requests fall within Jun 2023–Jun 2025
      query: "SELECT COUNT(*) FROM fact.takedown_requests WHERE period < '2023-06' OR period > '2025-06'"
      value: 0
@bruin */

WITH base AS (
    SELECT
        gt.country,
        gt.period,
        gt.half_year_label,
        gt.product,
        gt.reason,
        gt.request_count,
        gt.item_count,
        gt.extracted_at
    FROM stg.google_transparency gt
    INNER JOIN dims.country dc ON LOWER(gt.country) = LOWER(dc.country_code)
    INNER JOIN dims.platform dp ON LOWER(gt.product) = LOWER(dp.platform_name)
    INNER JOIN dims.reasons dr ON LOWER(gt.reason) = LOWER(dr.reason_name)
    INNER JOIN dims.periods dpd ON gt.period = dpd.period
)
SELECT * FROM base;
