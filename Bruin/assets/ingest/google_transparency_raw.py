/* @bruin
name: stg.google_transparency
type: duckdb.sql          # ← used only in 'dev' environment
connection: duckdb-google

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Cleaned Google Transparency takedown requests
owner: civil-liberties-pipeline

materialization:
    type: table
    strategy: create+replace

depends:
    - raw.google_transparency_requests
    - raw.google_transparency_detailed

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

WITH requests AS (
    SELECT
        LOWER(country) AS country,
        -- normalize textual time_period into YYYY-MM
        REPLACE(time_period, 'Jan-Jun ', '') AS half_year, -- example cleanup
        time_period AS period,
        product,
        reason,
        number_of_requests AS request_count,
        items_requested_removal AS item_count,
        extracted_at
    FROM raw.google_transparency_requests
    WHERE time_period IN ('Jul-Dec 2023','Jan-Jun 2024','Jul-Dec 2024','Jan-Jun 2025')
),
detailed AS (
    SELECT
        LOWER("Country/Region") AS country,
        strftime(CAST("Period Ending" AS DATE), '%Y-%m') AS period, -- convert MM/DD/YYYY → YYYY-MM
        Product AS product,
        Reason AS reason,
        Total AS request_count,
        Total AS item_count,
        extracted_at
    FROM raw.google_transparency_detailed
    WHERE CAST("Period Ending" AS DATE) BETWEEN DATE '2023-06-01' AND DATE '2025-06-30'
)

)
SELECT * FROM requests
UNION ALL
SELECT * FROM detailed;
