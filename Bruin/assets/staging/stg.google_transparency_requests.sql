/* @bruin
name: stg.google_transparency_requests
type: duckdb.sql
connection: duckdb-parquet

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Cleaned Google Transparency removal requests
owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace

depends:
  - load.google_transparency_requests_to_gcs
@bruin */

WITH raw AS (
    SELECT
        time_period,
        country,
        cldr_territory,
        requestor,
        product,
        reason,
        number_of_requests,
        items_requested_removal,
        items_removed_legal,
        items_removed_policy,
        extracted_at,
        -- Derived fields for easier analysis
        PARSE_DATE('%Y-%m', time_period) AS period_date,
        EXTRACT(YEAR FROM PARSE_DATE('%Y-%m', time_period)) AS year
    FROM {{ ref('load.google_transparency_requests_to_gcs') }}
)

SELECT * FROM raw;