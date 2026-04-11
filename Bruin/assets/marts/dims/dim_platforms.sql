/* @bruin
name: dim_platforms
type: duckdb.sql
connection: duckdb-parquet

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Unified list of platforms and services monitored
owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT DISTINCT
    product AS platform,
    'Google' AS source
FROM {{ ref('stg.google_transparency_requests') }}
WHERE country = 'Kenya'

UNION ALL

SELECT DISTINCT
    recipient AS platform,
    'Lumen' AS source
FROM {{ ref('stg.lumen_requests') }}
WHERE country = 'KE'

UNION ALL

SELECT DISTINCT
    test_name AS platform,
    'OONI' AS source
FROM {{ ref('stg.ooni') }}
WHERE country = 'KE';
