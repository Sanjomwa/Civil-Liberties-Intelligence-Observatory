/* @bruin
tags:
  - marts_bq
name: marts.dim_regions
type: bq.sql
connection: bigquery-default

description: Kenya regions/counties dimension derived from ACLED conflict data.

owner: civil-liberties-pipeline

depends:
  - stg.acled_conflict_events

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (

  SELECT DISTINCT
    country,
    region,
    admin1 AS county,
    centroid_latitude,
    centroid_longitude
  FROM `encoded-joy-485413-k5.stg.acled_conflict_events`
  WHERE country = 'Kenya'
    AND admin1 IS NOT NULL
),

aggregated AS (

  SELECT
    country,
    region,
    county,

    AVG(centroid_latitude) AS centroid_latitude,
    AVG(centroid_longitude) AS centroid_longitude

  FROM base
  GROUP BY country, region, county
)

SELECT
  FARM_FINGERPRINT(CONCAT(COALESCE(region, 'UNKNOWN'), '||', COALESCE(county, 'UNKNOWN'))) AS region_key,
  country,
  region,
  county,

  centroid_latitude,
  centroid_longitude,

  CASE
    WHEN county = 'Nairobi' THEN 'Capital'
    WHEN county IN ('Mombasa','Kisumu','Nakuru','Eldoret') THEN 'Major Urban'
    WHEN region = 'Coast' THEN 'Coast Region'
    WHEN region = 'Rift Valley' THEN 'Rift Valley'
    WHEN region = 'Nyanza' THEN 'Nyanza'
    WHEN region = 'Western' THEN 'Western'
    WHEN region = 'Central' THEN 'Central'
    WHEN region = 'Eastern' THEN 'Eastern'
    WHEN region = 'North Eastern' THEN 'North Eastern'
    ELSE 'Other'
  END AS region_group

FROM aggregated;