/* @bruin
name: stg.lumen_requests
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
  - load.lumen_requests_to_gcs
@bruin */

WITH raw AS (
    SELECT
        request_id,
        country,
        sender,
        recipient,
        date_submitted,
        period,
        half_year_label,
        reason,
        request_count,
        item_count,
        extracted_at,
        DATE(date_submitted) AS measurement_date,
        EXTRACT(YEAR FROM date_submitted) AS year
    FROM {{ ref('load.lumen_requests_to_gcs') }}
)

SELECT * FROM raw;
