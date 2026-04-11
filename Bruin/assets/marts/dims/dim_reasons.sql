/* @bruin
name: dim_reasons
type: duckdb.sql
connection: duckdb-parquet

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Standardized takedown and censorship reasons
owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT DISTINCT reason
FROM (
    SELECT reason FROM {{ ref('stg.google_transparency_requests') }} WHERE country = 'Kenya'
    UNION ALL
    SELECT reason FROM {{ ref('stg.google_transparency_detailed') }} WHERE country_region = 'Kenya'
    UNION ALL
    SELECT reason FROM {{ ref('stg.lumen_requests') }} WHERE country = 'KE'
) 
WHERE reason IS NOT NULL;
