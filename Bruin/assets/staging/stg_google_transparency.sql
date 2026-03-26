/* @bruin
name: stg.google_transparency
type: duckdb.sql
connection: duckdb-parquet

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
    - ingest.google_transparency_requests
    - ingest.google_transparency_detailed

columns:
    - name: country
      type: STRING
      checks: [{ name: not_null }]
    - name: period
      type: STRING
      checks: [{ name: not_null }]
    - name: half_year_label
      type: STRING
    - name: product
      type: STRING
    - name: reason
      type: STRING
    - name: request_count
      type: INTEGER
      checks: [{ name: not_null }]
    - name: item_count
      type: INTEGER
    - name: extracted_at
      type: TIMESTAMP

custom_checks:
    - name: non_negative_counts
      query: "SELECT COUNT(*) FROM {{ this }} WHERE request_count < 0 OR item_count < 0"
      value: 0
@bruin */

WITH requests AS (
    SELECT
        LOWER(country) AS country,
        -- Extract year and assign half-year dynamically
        regexp_extract(time_period, '([0-9]{4})', 1) ||
        CASE
            WHEN LOWER(time_period) LIKE 'january%' THEN '-06'
            WHEN LOWER(time_period) LIKE 'july%'    THEN '-12'
        END AS period,
        time_period AS half_year_label,
        product,
        reason,
        number_of_requests AS request_count,
        items_requested_removal AS item_count,
        extracted_at
    FROM parquet_scan('/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/google/google_transparency_requests.parquet')
),
detailed AS (
    SELECT
        LOWER(country_region) AS country,
        -- Parse slash-delimited dates like "6/30/2011"
        strftime(try_cast(period_ending AS TIMESTAMP), '%Y-%m') AS period,
        CASE
            WHEN strftime(try_cast(period_ending AS TIMESTAMP), '%m') = '06'
                 THEN 'Jan-Jun ' || strftime(try_cast(period_ending AS TIMESTAMP), '%Y')
            WHEN strftime(try_cast(period_ending AS TIMESTAMP), '%m') = '12'
                 THEN 'Jul-Dec ' || strftime(try_cast(period_ending AS TIMESTAMP), '%Y')
        END AS half_year_label,
        product,
        reason,
        total AS request_count,
        total AS item_count,
        extracted_at
    FROM parquet_scan('/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/google/google_transparency_detailed.parquet')
    WHERE try_cast(period_ending AS DATE) BETWEEN DATE '2011-06-30' AND DATE '2025-06-30'
)

SELECT * FROM requests
UNION ALL
SELECT * FROM detailed;
