/* @bruin
name: fact_takedown_requests
type: duckdb.sql
connection: duckdb-parquet

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Combined Google and Lumen takedown requests (Kenya only)
owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace

depends:
  - stg.google_transparency_requests
  - stg.google_transparency_detailed
  - stg.lumen_requests
@bruin */

SELECT 
    'google' AS source,
    country,
    product,
    reason,
    time_period,
    number_of_requests,
    items_requested_removal,
    extracted_at,
    period_date AS measurement_date
FROM {{ ref('stg.google_transparency_requests') }}
WHERE country = 'Kenya'

UNION ALL

SELECT 
    'google_detailed' AS source,
    country_region AS country,
    product,
    reason,
    NULL AS time_period,
    total AS number_of_requests,
    NULL AS items_requested_removal,
    extracted_at,
    period_date AS measurement_date
FROM {{ ref('stg.google_transparency_detailed') }}
WHERE country_region = 'Kenya'

UNION ALL

SELECT 
    'lumen' AS source,
    country,
    recipient AS product,
    reason,
    period AS time_period,
    request_count AS number_of_requests,
    item_count AS items_requested_removal,
    extracted_at,
    DATE(date_submitted) AS measurement_date
FROM {{ ref('stg.lumen_requests') }}
WHERE country = 'KE';
