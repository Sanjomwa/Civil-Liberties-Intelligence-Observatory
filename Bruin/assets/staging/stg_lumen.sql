/* @bruin
name: stg.lumen
type: duckdb.sql          # ← used only in 'dev' environment
connection: duckdb-lumen

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Cleaned Lumen takedown requests
owner: civil-liberties-pipeline

materialization:
    type: table
    strategy: create+replace

depends:
    - raw.lumen_requests

columns:
    - name: request_id
      type: STRING
      description: Unique request identifier
      primary_key: true
      checks:
        - name: not_null
        - name: unique
    - name: country
      type: STRING
      description: Country issuing request
      checks:
        - name: not_null
    - name: sender
      type: STRING
      description: Entity sending request
    - name: recipient
      type: STRING
      description: Platform or service targeted
      checks:
        - name: not_null
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
    - name: valid_date_range
      description: Ensure requests fall within Jun 2023–Jun 2025
      query: "SELECT COUNT(*) FROM stg.lumen WHERE CAST(date_submitted AS DATE) < CAST('2023-06-01' AS DATE) OR CAST(date_submitted AS DATE) > CAST('2025-06-30' AS DATE)"
      value: 0
@bruin */

WITH raw AS (
    SELECT
        request_id,
        UPPER(country) AS country,          -- normalize to KE
        TRIM(sender) AS sender,             -- clean whitespace
        LOWER(recipient) AS recipient,      -- normalize platform names
        CAST(date_submitted AS TIMESTAMP) AS date_submitted,
        -- normalize to YYYY-MM
        strftime(CAST(date_submitted AS DATE), '%Y-%m') AS period,
        -- derive half-year label
        CASE
            WHEN strftime(CAST(date_submitted AS DATE), '%m') IN ('01','02','03','04','05','06')
                 THEN 'Jan-Jun ' || strftime(CAST(date_submitted AS DATE), '%Y')
            WHEN strftime(CAST(date_submitted AS DATE), '%m') IN ('07','08','09','10','11','12')
                 THEN 'Jul-Dec ' || strftime(CAST(date_submitted AS DATE), '%Y')
        END AS half_year_label,
        reason,
        extracted_at
    FROM raw.lumen_requests
    WHERE CAST(date_submitted AS DATE) BETWEEN CAST('2023-06-01' AS DATE) AND CAST('2025-06-30' AS DATE)
)

SELECT * FROM raw;
