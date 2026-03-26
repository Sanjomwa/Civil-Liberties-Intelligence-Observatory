/* @bruin
name: fact.takedown_requests
type: duckdb.sql          # ← used only in 'dev' environment
connection: duckdb-parquet

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Fact table for Google Transparency + Lumen takedown requests
owner: civil-liberties-pipeline

materialization:
    type: table
    strategy: create+replace

depends:
    - stg.google_transparency
    - stg.lumen
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
    - name: platform
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

WITH google AS (
    SELECT
        gt.country,
        strftime(CAST(gt.time_period AS DATE), '%Y-%m') AS period,
        CASE
            WHEN EXTRACT(MONTH FROM CAST(gt.time_period AS DATE)) BETWEEN 1 AND 6
                 THEN 'Jan-Jun ' || EXTRACT(YEAR FROM CAST(gt.time_period AS DATE))
            ELSE 'Jul-Dec ' || EXTRACT(YEAR FROM CAST(gt.time_period AS DATE))
        END AS half_year_label,
        gt.product AS platform,
        gt.reason,
        gt.number_of_requests AS request_count,
        gt.items_requested_removal AS item_count,
        gt.extracted_at
    FROM stg.google_transparency gt
    WHERE CAST(gt.time_period AS DATE) BETWEEN DATE '2023-06-01' AND DATE '2025-06-30'
),
lumen AS (
    SELECT
        l.country,
        l.period,
        l.half_year_label,
        l.recipient AS platform,
        l.reason,
        l.request_count,
        l.item_count,
        l.extracted_at
    FROM stg.lumen l
)

SELECT
    c.country,
    f.period,
    f.half_year_label,
    p.platform_name AS platform,
    r.reason_name AS reason,
    f.request_count,
    f.item_count,
    f.extracted_at
FROM (
    SELECT * FROM google
    UNION ALL
    SELECT * FROM lumen
) f
JOIN dims.country c
  ON LOWER(TRIM(f.country)) = LOWER(TRIM(c.country_code))
JOIN dims.platform p
  ON LOWER(TRIM(f.platform)) = LOWER(TRIM(p.platform_name))
JOIN dims.reasons r
  ON LOWER(TRIM(f.reason)) = LOWER(TRIM(r.reason_name))
JOIN dims.periods dp
  ON f.period = dp.period;
