/* @bruin
name: fact.lumen_platforms
type: duckdb.sql          # ← used only in 'dev' environment
connection: duckdb-mart

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Fact table for Lumen takedown requests, joined with platform dimension
owner: civil-liberties-pipeline

materialization:
    type: table
    strategy: create+replace

depends:
    - stg.lumen
    - dims.platform
    - dims.country
    - dims.periods

columns:
    - name: request_id
      type: STRING
      description: Unique request identifier
      primary_key: true
      checks:
        - name: not_null
        - name: unique
    - name: platform_id
      type: STRING
      description: Normalized platform identifier
      checks:
        - name: not_null
    - name: country
      type: STRING
      description: Country issuing request
      checks:
        - name: not_null
    - name: sender
      type: STRING
      description: Entity sending request
    - name: date_submitted
      type: TIMESTAMP
      description: When request was submitted
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
    - name: reason
      type: STRING
      description: Reason for takedown
    - name: extracted_at
      type: TIMESTAMP
      description: Pipeline extraction timestamp

custom_checks:
    - name: valid_period_range
      description: Ensure requests fall within Jun 2023–Jun 2025
      query: "SELECT COUNT(*) FROM fact.lumen_platforms WHERE period < '2023-06' OR period > '2025-06'"
      value: 0
@bruin */

WITH joined AS (
    SELECT
        s.request_id,
        d.platform_id,
        s.country,
        s.sender,
        s.date_submitted,
        s.period,
        s.half_year_label,
        s.reason,
        s.extracted_at
    FROM stg.lumen s
    LEFT JOIN dims.platform d
      ON LOWER(s.recipient) = LOWER(d.platform_name)
    LEFT JOIN dims.country c
      ON LOWER(s.country) = LOWER(c.country_code)
    LEFT JOIN dims.periods p
      ON s.period = p.period
)

SELECT * FROM joined;
