/* @bruin
name: dim_regions
type: duckdb.sql
connection: duckdb-parquet

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Kenya administrative regions from ACLED
owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace

depends:
  - stg.acled_conflict_events
@bruin */

SELECT DISTINCT
    country,
    region,
    admin1,
    centroid_latitude,
    centroid_longitude
FROM {{ ref('stg.acled_conflict_events') }}
WHERE country = 'Kenya'
ORDER BY region, admin1;
