/* @bruin
name: stg.lumen
type: duckdb.sql
connection: duckdb-parquet

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
  - name: request_count
    type: INTEGER
    description: Always 1 for mock records
  - name: item_count
    type: INTEGER
    description: Always 1 for mock records
  - name: extracted_at
    type: TIMESTAMP
    description: Pipeline extraction timestamp

custom_checks:
  - name: valid_date_range
    description: Ensure requests fall within Jun 2023–Jun 2025
    query: "SELECT COUNT(*) FROM {{ this }} WHERE CAST(date_submitted AS DATE) < CAST('2023-06-01' AS DATE) OR CAST(date_submitted AS DATE) > CAST('2025-06-30' AS DATE)"
    value: 0
@bruin */

WITH raw AS (
    SELECT
        request_id,
        UPPER(country) AS country,
        TRIM(sender) AS sender,
        LOWER(recipient) AS recipient,
        CAST(date_submitted AS TIMESTAMP) AS date_submitted,
        period,
        half_year_label,
        reason,
        request_count,
        item_count,
        extracted_at
    FROM dev_raw.lumen_requests   -- ✅ Bruin resolves this to dev_raw.lumen_requests in dev
    WHERE CAST(date_submitted AS DATE) BETWEEN CAST('2023-06-01' AS DATE) AND CAST('2025-06-30' AS DATE)
)

SELECT * FROM raw;
